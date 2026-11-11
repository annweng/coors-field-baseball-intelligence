import numpy as np
import pandas as pd

from models.advanced.feature_matrix import append_baseline_probas, encode_matrix
from models.baseline.forecaster import BaselineForecaster


def test_baseline_stack_columns_in_matrix() -> None:
    train_outcomes = pd.DataFrame({"outcome": ["single", "strikeout", "walk"]})
    row = {
        "batt_pa_30d": 40,
        "pitch_pa_30d": 40,
        "batt_pa_season": 100,
        "pitch_pa_season": 100,
        "batter_stands": "R",
        "pitcher_throws": "R",
        "is_coors": 0,
        **{f"batt_{o}_rate_30d": 0.125 for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
        **{f"pitch_{o}_rate_30d": 0.125 for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
        **{f"batt_{o}_rate_season": 0.125 for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
        **{f"pitch_{o}_rate_season": 0.125 for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
        "outcome": "single",
    }
    frame = pd.DataFrame([row])
    base = BaselineForecaster().fit(train_outcomes)
    stacked = append_baseline_probas(frame, base)
    x, cols = encode_matrix(stacked, compact=True)
    assert any(c.startswith("base_p_") for c in cols)
    assert abs(stacked[[c for c in stacked.columns if c.startswith("base_p_")]].sum(axis=1).iloc[0] - 1.0) < 1e-6
