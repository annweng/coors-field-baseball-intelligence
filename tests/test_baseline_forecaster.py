import numpy as np
import pandas as pd

from models.baseline.forecaster import BaselineForecaster


def test_predicted_probabilities_sum_to_one():
    train = pd.DataFrame(
        {
            "outcome": ["strikeout", "single", "walk", "home_run"],
        }
    )
    pred = pd.DataFrame(
        {
            "batt_pa_30d": [50, 10],
            "pitch_pa_30d": [50, 10],
            **{f"batt_{o}_rate_30d": [0.25, np.nan] for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
            **{f"pitch_{o}_rate_30d": [0.22, 0.22] for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
            **{f"batt_{o}_rate_season": [0.25, 0.1] for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
            **{f"pitch_{o}_rate_season": [0.22, 0.22] for o in ("strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out")},
            "batt_pa_season": [100, 5],
            "pitch_pa_season": [100, 5],
        }
    )
    model = BaselineForecaster().fit(train)
    probs = model.predict_proba(pred)
    assert probs.shape == (2, 8)
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, rtol=1e-6)
