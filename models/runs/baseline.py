"""Naive team runs baselines from rolling averages and park."""

from __future__ import annotations

import numpy as np
import pandas as pd


class RunsBaseline:
    """Predict runs scored as blend of team offense, opponent pitching proxy, and home edge."""

    def __init__(self, *, home_edge: float = 0.15) -> None:
        self.home_edge = home_edge
        self.league_runs_: float = 4.5

    def fit(self, train: pd.DataFrame) -> RunsBaseline:
        self.league_runs_ = float(train["runs_scored"].mean())
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        team_off = frame["team_rs_30d"].fillna(frame["team_rs_season"]).fillna(self.league_runs_)
        opp_def = frame["opp_ra_30d"].fillna(self.league_runs_)
        base = 0.55 * team_off + 0.45 * opp_def
        home_bump = frame["is_home"].astype(float) * self.home_edge
        park = np.where(frame["is_coors"].astype(bool), 0.35, 0.0)
        return np.maximum(0.5, base + home_bump + park)
