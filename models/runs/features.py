"""Feature matrix for team run models."""

from __future__ import annotations

import pandas as pd


def feature_columns() -> list[str]:
    return [
        "is_home",
        "is_coors",
        "team_rs_30d",
        "team_ra_30d",
        "team_rs_season",
        "team_ra_season",
        "opp_rs_30d",
        "opp_ra_30d",
    ]


def encode_matrix(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cols = feature_columns()
    x = frame[cols].astype(float).fillna(0.0)
    return x, cols
