# tiny-chess-01

A 4 KB chess engine in Python (MIT). `main.py` is an LZMA payload
(base85) that unpacks to the engine: 0x88 board, negamax with
alpha-beta, iterative deepening to a fixed 30,000-node budget,
quiescence search (captures, promotions, check evasions), a
transposition table with Zobrist hashing, MVV-LVA move ordering,
and material plus piece-square evaluation mirroring the house
gauntlet's tables, with tapered king safety and the bishop pair.
Repetition positions score 0. No clock, no randomness: the same
position always gets the same move, so replays match.

It plays the gauntlet through the env at `MAKEFUN_ENV_URL`
(`POST /game`, `POST /move`), one game after another, and exits
when the env reports done.
