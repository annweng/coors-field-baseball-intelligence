"""Calibration diagnostics."""

from __future__ import annotations

import numpy as np

from data_pipeline.features.constants import OUTCOME_CLASSES


def reliability_bins(
    y_true: list[str],
    probas: np.ndarray,
    *,
    n_bins: int = 10,
    outcome: str = "home_run",
) -> dict:
    idx = OUTCOME_CLASSES.index(outcome)
    p = probas[:, idx]
    y = np.array([1 if t == outcome else 0 for t in y_true])
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.digitize(p, bins) - 1
    points = []
    for b in range(n_bins):
        mask = bin_ids == b
        if mask.sum() == 0:
            continue
        points.append(
            {
                "bin": b,
                "mean_predicted": float(p[mask].mean()),
                "empirical_rate": float(y[mask].mean()),
                "count": int(mask.sum()),
            }
        )
    return {"outcome": outcome, "points": points}
