# Feature engineering (Milestone 4)

Rolling features are computed in `data_pipeline/features/rolling.py` with **shift(1)** so the current plate appearance never enters its own history.

## Windows

| Window | Column suffix | Definition |
|--------|---------------|------------|
| 7 days | `_7d` | Calendar rolling on `game_date` |
| 30 days | `_30d` | Calendar rolling |
| 60 days | `_60d` | Calendar rolling |
| Season to date | `_season` | Cumulative within `season` |

## Batter (`batt_`)

Per batter: PA count, outcome rates (8 classes), rolling wOBA (outcome-weighted proxy).

## Pitcher (`pitch_`)

Same structure for pitcher allowed outcomes.

## Context

- `is_coors` — stadium id 19 / 3312
- Handedness columns from plate appearances (`batter_stands`, `pitcher_throws`) reserved for Milestone 5

## Training filter

Baseline training excludes `unknown` outcomes and rows with fewer than **5** prior PAs (30d) for batter and pitcher.
