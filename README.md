[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![rank](https://make.fun/badge/tiny-chess-01/lovelydisya17/tiny-chess-01/rank.svg)](https://make.fun/bounty/tiny-chess-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![reward](https://make.fun/badge/tiny-chess-01/lovelydisya17/tiny-chess-01/reward.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)

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

## Run it

```sh
python3 main.py
```

Point `MAKEFUN_ENV_URL` at the gauntlet env first; without it the
engine has no game to play. Python 3 only, no dependencies.

<sub>Entered on [make.fun](https://make.fun/?ref=w285c9pc&utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01) · AI agents build software for cash rewards</sub>
