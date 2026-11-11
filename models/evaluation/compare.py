"""Compare advanced model vs baseline on the same holdout frame."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.baseline.forecaster import BaselineForecaster
from models.evaluation.metrics import evaluate_multiclass


def baseline_on_split(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    model = BaselineForecaster()
    model.fit(train)
    probas = model.predict_proba(test)
    return evaluate_multiclass(test["outcome"].tolist(), probas)


def better_than_baseline(advanced_ll: float, baseline_ll: float, *, margin: float = 0.01) -> bool:
    return advanced_ll < baseline_ll - margin
