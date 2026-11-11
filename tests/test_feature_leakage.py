"""Ensure rolling features do not include the current plate appearance."""

import pandas as pd

from data_pipeline.features.rolling import build_rolling_features


def test_future_pa_does_not_change_prior_features():
    base = pd.DataFrame(
        [
            {
                "game_pk": 1,
                "at_bat_number": 1,
                "batter_id": 100,
                "pitcher_id": 200,
                "game_date": "2024-06-01",
                "season": 2024,
                "outcome": "strikeout",
            },
            {
                "game_pk": 1,
                "at_bat_number": 2,
                "batter_id": 100,
                "pitcher_id": 200,
                "game_date": "2024-06-02",
                "season": 2024,
                "outcome": "single",
            },
        ]
    )
    full = build_rolling_features(base)
    truncated = build_rolling_features(base.iloc[:1])
    col = "batt_strikeout_rate_30d"
    full_val = full.iloc[0][col]
    trunc_val = truncated.iloc[0][col]
    assert pd.isna(full_val) or full_val == trunc_val


def test_shift_excludes_current_pa_from_season_count():
    df = pd.DataFrame(
        [
            {
                "game_pk": 1,
                "at_bat_number": 1,
                "batter_id": 50,
                "pitcher_id": 60,
                "game_date": "2024-07-10",
                "season": 2024,
                "outcome": "walk",
            },
            {
                "game_pk": 2,
                "at_bat_number": 1,
                "batter_id": 50,
                "pitcher_id": 60,
                "game_date": "2024-07-11",
                "season": 2024,
                "outcome": "home_run",
            },
        ]
    )
    feat = build_rolling_features(df)
    assert feat.iloc[1]["batt_pa_season"] == 1
