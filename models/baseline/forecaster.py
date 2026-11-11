"""Multinomial baseline forecaster from rolling rate features."""

from __future__ import annotations

import numpy as np

from data_pipeline.features.constants import OUTCOME_CLASSES


class BaselineForecaster:
    """
    Smoothed blend of batter, pitcher, and league outcome rates.

    Uses 30-day rolling rate columns when present; falls back to season-to-date.
    """

    def __init__(
        self,
        *,
        smoothing: float = 75.0,
        weight_batter: float = 0.45,
        weight_pitcher: float = 0.45,
        weight_league: float = 0.10,
    ) -> None:
        if not np.isclose(weight_batter + weight_pitcher + weight_league, 1.0):
            raise ValueError("Blend weights must sum to 1.0")
        self.smoothing = smoothing
        self.weight_batter = weight_batter
        self.weight_pitcher = weight_pitcher
        self.weight_league = weight_league
        self.league_probs_: np.ndarray | None = None

    def fit(self, train_df) -> BaselineForecaster:
        counts = np.zeros(len(OUTCOME_CLASSES), dtype=float)
        for i, outcome in enumerate(OUTCOME_CLASSES):
            counts[i] = (train_df["outcome"] == outcome).sum()
        total = counts.sum()
        alpha = self.smoothing / len(OUTCOME_CLASSES)
        self.league_probs_ = (counts + alpha) / (total + self.smoothing)
        return self

    def _row_dist(self, row, prefix: str) -> np.ndarray:
        pa = row.get(f"{prefix}_pa_30d")
        if pa is None or (isinstance(pa, float) and np.isnan(pa)) or pa <= 0:
            pa = row.get(f"{prefix}_pa_season", 0)
        pa = 0.0 if pa is None or (isinstance(pa, float) and np.isnan(pa)) else float(pa)

        probs = np.zeros(len(OUTCOME_CLASSES), dtype=float)
        alpha = self.smoothing / len(OUTCOME_CLASSES)
        for i, outcome in enumerate(OUTCOME_CLASSES):
            rate = row.get(f"{prefix}_{outcome}_rate_30d")
            if rate is None or (isinstance(rate, float) and np.isnan(rate)):
                rate = row.get(f"{prefix}_{outcome}_rate_season", np.nan)
            if rate is None or (isinstance(rate, float) and np.isnan(rate)):
                rate = self.league_probs_[i]
            probs[i] = rate * pa + alpha
        return probs / probs.sum()

    def predict_proba(self, df) -> np.ndarray:
        if self.league_probs_ is None:
            raise RuntimeError("Call fit() before predict_proba()")
        out = np.zeros((len(df), len(OUTCOME_CLASSES)), dtype=float)
        league = self.league_probs_
        for idx, (_, row) in enumerate(df.iterrows()):
            row_dict = row.to_dict()
            b = self._row_dist(row_dict, "batt")
            p = self._row_dist(row_dict, "pitch")
            blended = (
                self.weight_batter * b
                + self.weight_pitcher * p
                + self.weight_league * league
            )
            out[idx] = blended / blended.sum()
        return out
