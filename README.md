# The World in One Day — 23 November 2026

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/moodforput/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/moodforput/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A program that writes one image summing up the world news of Monday
23 November 2026, for the make.fun bounty `news-image-20261123`.

## What it makes

A 1024 by 1024 PNG newspaper front page, `entry.png`, with the date
`MONDAY - 23 NOVEMBER 2026` in the masthead and six stories in a
2 by 3 grid:

1. India vs New Zealand, 1st Test, Day 5 — India declare 720/9, NZ 157/4
   at lunch at Basin Reserve.
2. FIFA confirms the UK will host the 2035 Women's World Cup.
3. Democrats clinch the House majority.
4. India's Youth Congress protests Meta.
5. Nine shot at a central California concert, one critical.
6. Elderly man rescued after 11 days in the Amazon.

## Run

```sh
python3 main.py
```

Writes `entry.png` to `$MAKEFUN_OUTPUT_DIR` (or `/output` when unset).
Python 3.13, standard library only, no network, deterministic: two runs
produce byte-identical output.

## Test

```sh
python3 -m unittest discover -s test -v
```

## How it works

`main.py` is a single self-contained file: its own PNG encoder (zlib +
CRC32), its own rasterizer (rectangles, lines, circles, triangles) and its
own 5x7 bitmap font. Each story gets a panel with a coloured kicker strip,
a two-line headline, a detail line and a small flat pictorial cue (cricket
pitch, football, Capitol dome, protest placards, concert stage, jungle
river).
