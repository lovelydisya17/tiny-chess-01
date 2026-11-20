# Tiny chess engine: 0x88 board, negamax + alpha-beta, transposition
# table, quiescence search, material + piece-square evaluation.
# Fixed 30,000-node budget, no clock, no randomness: the same
# position always gives the same move, so trial replays match.
import json, os, random, urllib.request as req

# Pieces: 1 pawn, 2 knight, 3 bishop, 4 rook, 5 queen, 6 king.
VAL = [0, 100, 320, 330, 500, 900, 0]
KNIGHT = [31, 33, 14, 18, -31, -33, -14, -18]
KING = [15, 16, 17, 1, -1, -15, -16, -17]
ROOK = [16, -16, 1, -1]
BISHOP = [15, 17, -15, -17]
PRANK = [0, 0, 4, 8, 14, 24, 40, 0]
PFILE = [0, 0, 0, 10, 15, 10, 5, 0]
KFILE = [20, 25, 10, 0, 0, 10, 25, 20]
MATE = 100000
BUDGET = 30000

board = [0] * 128
side = 1
castle = 0
ep = -1
hkey = 0
table = {}
seen = set()
path = []
undo = []
nodes = [0]
_rng = random.Random(987654321)
Z = [_rng.getrandbits(64) for _ in range(1561)]


class NoNodes(Exception):
    pass


def zkey(p, sq):
    return Z[(p + 6 if p < 0 else p + 5) * 128 + sq]


def chash():
    h = 0
    for sq in range(128):
        if sq & 0x88:
            continue
        p = board[sq]
        if p:
            h ^= zkey(p, sq)
    h ^= Z[1536 + castle]
    if ep >= 0:
        h ^= Z[1552 + (ep & 7)]
    if side < 0:
        h ^= Z[1560]
    return h


def loadfen(fen):
    global side, castle, ep, hkey
    f = fen.split()
    for sq in range(128):
        board[sq] = 0
    kind = {'p': 1, 'n': 2, 'b': 3, 'r': 4, 'q': 5, 'k': 6}
    for r, row in enumerate(f[0].split('/')):
        file = 0
        for ch in row:
            if ch.isdigit():
                file += int(ch)
            else:
                board[(7 - r) * 16 + file] = kind[ch.lower()] * (1 if ch.isupper() else -1)
                file += 1
    side = 1 if f[1] == 'w' else -1
    castle = 0
    if 'K' in f[2]:
        castle |= 1
    if 'Q' in f[2]:
        castle |= 2
    if 'k' in f[2]:
        castle |= 4
    if 'q' in f[2]:
        castle |= 8
    ep = -1 if f[3] == '-' else (int(f[3][1]) - 1) * 16 + ord(f[3][0]) - 97
    hkey = chash()


def atk(sq, by):
    for t in ((sq - 15, sq - 17) if by > 0 else (sq + 15, sq + 17)):
        if not t & 0x88 and board[t] == by:
            return True
    for d in KNIGHT:
        t = sq + d
        if not t & 0x88 and board[t] == 2 * by:
            return True
    for d in KING:
        t = sq + d
        if not t & 0x88 and board[t] == 6 * by:
            return True
    for d in ROOK:
        t = sq + d
        while not t & 0x88:
            v = board[t]
            if v:
                if v == 4 * by or v == 5 * by:
                    return True
                break
            t += d
    for d in BISHOP:
        t = sq + d
        while not t & 0x88:
            v = board[t]
            if v:
                if v == 3 * by or v == 5 * by:
                    return True
                break
            t += d
    return False


def ksq(colour):
    for sq in range(128):
        if board[sq] == 6 * colour:
            return sq
    return -1


def promo(moves, frm, to):
    if (side > 0 and to >> 4 == 7) or (side < 0 and to >> 4 == 0):
        for p in (5, 4, 3, 2):
            moves.append(frm | to << 7 | p << 14)
    else:
        moves.append(frm | to << 7)


def castling(moves):
    if side > 0:
        if castle & 1 and not board[5] and not board[6] and board[7] == 4 \
                and not atk(4, -1) and not atk(5, -1) and not atk(6, -1):
            moves.append(4 | 6 << 7)
        if castle & 2 and not board[3] and not board[2] and not board[1] and board[0] == 4 \
                and not atk(4, -1) and not atk(3, -1) and not atk(2, -1):
            moves.append(4 | 2 << 7)
    else:
        if castle & 4 and not board[117] and not board[118] and board[119] == -4 \
                and not atk(116, 1) and not atk(117, 1) and not atk(118, 1):
            moves.append(116 | 118 << 7)
        if castle & 8 and not board[115] and not board[114] and not board[113] and board[112] == -4 \
                and not atk(116, 1) and not atk(115, 1) and not atk(114, 1):
            moves.append(116 | 114 << 7)


def gen(caps):
    moves = []
    for frm in range(128):
        if frm & 0x88:
            continue
        v = board[frm]
        if not v or (v > 0) != (side > 0):
            continue
        t = abs(v)
        if t == 1:
            step = 16 * side
            ahead = frm + step
            if not ahead & 0x88 and not board[ahead]:
                if not caps:
                    promo(moves, frm, ahead)
                    if frm >> 4 == (1 if side > 0 else 6) and not board[frm + 2 * step]:
                        moves.append(frm | (frm + 2 * step) << 7)
                elif (side > 0 and ahead >> 4 == 7) or (side < 0 and ahead >> 4 == 0):
                    promo(moves, frm, ahead)
            for to in (frm + step - 1, frm + step + 1):
                if to & 0x88:
                    continue
                if board[to] and (board[to] > 0) != (side > 0):
                    promo(moves, frm, to)
                elif to == ep:
                    moves.append(frm | to << 7)
        elif t in (2, 6):
            for d in (KNIGHT if t == 2 else KING):
                to = frm + d
                if not to & 0x88 and ((not caps and not board[to]) or
                                      (board[to] and (board[to] > 0) != (side > 0))):
                    moves.append(frm | to << 7)
            if t == 6 and not caps:
                castling(moves)
        else:
            dirs = ROOK if t == 4 else BISHOP if t == 3 else ROOK + BISHOP
            for d in dirs:
                to = frm + d
                while not to & 0x88:
                    x = board[to]
                    if x:
                        if (x > 0) != (side > 0):
                            moves.append(frm | to << 7)
                        break
                    if not caps:
                        moves.append(frm | to << 7)
                    to += d
    return moves


def make(move):
    global side, castle, ep, hkey
    frm, to, pr = move & 127, move >> 7 & 127, move >> 14
    v = board[frm]
    w = board[to]
    tsq = to
    oc, oe, oh = castle, ep, hkey
    h = oh ^ zkey(v, frm) ^ Z[1560]
    if abs(v) == 1 and to == ep and not w:
        tsq = to - 16 * side
        w = board[tsq]
        board[tsq] = 0
    if w:
        h ^= zkey(w, tsq)
    moved = pr * side if pr else v
    h ^= zkey(moved, to)
    board[to] = moved
    board[frm] = 0
    if abs(v) == 6 and abs(to - frm) == 2:
        if to > frm:
            h ^= zkey(board[to + 1], to + 1) ^ zkey(board[to + 1], to - 1)
            board[to - 1] = board[to + 1]
            board[to + 1] = 0
        else:
            h ^= zkey(board[to - 2], to - 2) ^ zkey(board[to - 2], to + 1)
            board[to + 1] = board[to - 2]
            board[to - 2] = 0
    if frm == 4 or to == 4:
        castle &= ~3
    if frm == 0 or to == 0:
        castle &= ~2
    if frm == 7 or to == 7:
        castle &= ~1
    if frm == 116 or to == 116:
        castle &= ~12
    if frm == 112 or to == 112:
        castle &= ~8
    if frm == 119 or to == 119:
        castle &= ~4
    if oe >= 0:
        h ^= Z[1552 + (oe & 7)]
    ep = frm + 16 * side if abs(v) == 1 and abs(to - frm) == 32 else -1
    if ep >= 0:
        h ^= Z[1552 + (ep & 7)]
    h ^= Z[1536 + oc] ^ Z[1536 + castle]
    hkey = h
    path.append(h)
    side = -side
    undo.append((move, w, tsq, oc, oe, oh))


def unmake():
    global side, castle, ep, hkey
    move, w, tsq, oc, oe, oh = undo.pop()
    hkey = oh
    path.pop()
    frm, to, pr = move & 127, move >> 7 & 127, move >> 14
    side = -side
    moved = board[to]
    board[frm] = side if pr else moved
    board[to] = 0
    if w:
        board[tsq] = w
    if abs(moved) == 6 and abs(to - frm) == 2:
        if to > frm:
            board[to + 1] = board[to - 1]
            board[to - 1] = 0
        else:
            board[to - 2] = board[to + 1]
            board[to + 1] = 0
    castle, ep = oc, oe


def ev():
    score = 0
    np = 0
    bish = [0, 0]
    kg = [0, 0]
    for rank in range(8):
        for file in range(8):
            v = board[rank * 16 + file]
            if not v:
                continue
            t = abs(v)
            white = v > 0
            rel = rank if white else 7 - rank
            centre = min(file, 7 - file) + min(rel, 7 - rel)
            if t == 6:
                kg[0 if white else 1] = rel * 8 + file
                continue
            if t == 1:
                x = 100 + PRANK[rel] + (PFILE[rel] if file in (3, 4) else 0)
            elif t == 2:
                x = 320 + 6 * centre - 20
            elif t == 3:
                x = 330 + 4 * centre - 8
            elif t == 4:
                x = 500 + (15 if rel == 6 else 0) + (5 if rel == 0 and file in (3, 4) else 0)
            else:
                x = 900 + 2 * centre - 6
            score += x if white else -x
            np += VAL[t]
            if t == 3:
                bish[0 if white else 1] += 1
    total = 2 * (2 * 320 + 2 * 330 + 2 * 500 + 900)
    phase = min(np, total)
    for i in (0, 1):
        sq = kg[i]
        rank, file = sq >> 3, sq & 7
        centre = min(file, 7 - file) + min(rank, 7 - rank)
        kv = (KFILE[file] if rank == 0 else max(-50, -15 * rank)) * phase
        kv += (8 * centre - 24) * (total - phase)
        kv //= total
        score += kv if i == 0 else -kv
    if bish[0] >= 2:
        score += 30
    if bish[1] >= 2:
        score -= 30
    return score if side > 0 else -score


def order(moves, tt=0):
    def key(m):
        if m == tt:
            return -10 ** 9
        to = m >> 7 & 127
        v = board[to]
        if not v and abs(board[m & 127]) == 1 and to == ep:
            v = 1
        r = 0
        if v:
            r = 10 * VAL[abs(v)] - VAL[abs(board[m & 127])] // 10
        if m >> 14:
            r += 900
        return -r
    moves.sort(key=key)
    return moves


def qsearch(alpha, beta, ply):
    nodes[0] += 1
    if nodes[0] > BUDGET:
        raise NoNodes
    if hkey in seen or hkey in path[:-1]:
        return 0
    if atk(ksq(side), -side):
        moves = order(gen(False))
        best = -MATE
        legal = 0
        for m in moves:
            make(m)
            try:
                if atk(ksq(-side), side):
                    continue
                legal += 1
                v = -qsearch(-beta, -alpha, ply + 1)
            finally:
                unmake()
            if v > best:
                best = v
            if v > alpha:
                alpha = v
            if alpha >= beta:
                break
        return -MATE + ply if legal == 0 else best
    stand = ev()
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand
    for m in order(gen(True)):
        make(m)
        try:
            if atk(ksq(-side), side):
                continue
            v = -qsearch(-beta, -alpha, ply + 1)
        finally:
            unmake()
        if v > alpha:
            alpha = v
        if alpha >= beta:
            break
    return alpha


def search(depth, alpha, beta, ply):
    nodes[0] += 1
    if nodes[0] > BUDGET:
        raise NoNodes
    if depth <= 0:
        return qsearch(alpha, beta, ply)
    if hkey in seen or hkey in path[:-1]:
        return 0
    e = table.get(hkey)
    tt = 0
    if e and e[0] >= depth:
        if e[2] == 0:
            return e[1]
        if e[2] == 1 and e[1] >= beta:
            return e[1]
        if e[2] == 2 and e[1] <= alpha:
            return e[1]
        tt = e[3]
    moves = gen(False)
    if not moves:
        return -MATE + ply if atk(ksq(side), -side) else 0
    order(moves, tt)
    best, bestm = -MATE, 0
    start = alpha
    legal = 0
    for m in moves:
        make(m)
        try:
            if atk(ksq(-side), side):
                continue
            legal += 1
            v = -search(depth - 1, -beta, -alpha, ply + 1)
        finally:
            unmake()
        if v > best:
            best, bestm = v, m
        if v > alpha:
            alpha = v
        if alpha >= beta:
            break
    if legal == 0:
        return -MATE + ply if atk(ksq(side), -side) else 0
    if abs(best) < MATE - 1000:
        table[hkey] = (depth, best, 2 if best <= start else 1 if best >= beta else 0, bestm)
    return best


def to_uci(m):
    frm, to, p = m & 127, m >> 7 & 127, m >> 14
    s = chr(97 + (frm & 7)) + str((frm >> 4) + 1) + chr(97 + (to & 7)) + str((to >> 4) + 1)
    if p:
        s += {2: 'n', 3: 'b', 4: 'r', 5: 'q'}[p]
    return s


def from_uci(u):
    frm = (int(u[1]) - 1) * 16 + ord(u[0]) - 97
    to = (int(u[3]) - 1) * 16 + ord(u[2]) - 97
    p = 0
    if len(u) == 5:
        p = {'n': 2, 'b': 3, 'r': 4, 'q': 5}[u[4]]
    return frm | to << 7 | p << 14


def choose(fen, legal, moves):
    loadfen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    seen.clear()
    seen.add(hkey)
    for u in moves:
        make(from_uci(u))
        seen.add(hkey)
    loadfen(fen)
    if len(table) > 200000:
        table.clear()
    path.clear()
    path.append(hkey)
    root = [from_uci(u) for u in legal]
    if len(root) == 1:
        return to_uci(root[0])
    nodes[0] = 0
    order(root)
    best = root[0]
    for depth in range(1, 9):
        try:
            alpha = -MATE
            pick, top = best, -MATE
            for m in root:
                make(m)
                try:
                    if atk(ksq(-side), side):
                        continue
                    v = -search(depth - 1, -MATE, -alpha, 1)
                finally:
                    unmake()
                if v > top:
                    top, pick = v, m
                if v > alpha:
                    alpha = v
            best = pick
            root.remove(best)
            root.insert(0, best)
        except NoNodes:
            break
    return to_uci(best)


ENV = os.environ["MAKEFUN_ENV_URL"]


def post(path, body):
    q = req.Request(ENV + path, data=json.dumps(body).encode(),
                    headers={"content-type": "application/json"})
    try:
        with req.urlopen(q) as r:
            return json.load(r)
    except Exception:
        return None


while True:
    g = post("/game", {})
    if not g or g.get("status") == "done":
        break
    while g.get("status") == "your_move":
        m = choose(g["fen"], g["legal_moves"], g["moves"])
        r = post("/move", {"game": g["game"], "move": m})
        if not r:
            r = post("/move", {"game": g["game"], "move": g["legal_moves"][0]})
        g = r or {"status": "done"}
