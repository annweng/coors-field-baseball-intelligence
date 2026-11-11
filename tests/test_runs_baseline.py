import numpy as np
import pandas as pd

from models.runs.baseline import RunsBaseline


def test_runs_baseline_positive_predictions() -> None:
    train = pd.DataFrame({"runs_scored": [4.0, 5.0, 3.0, 6.0]})
    frame = pd.DataFrame(
        {
            "team_rs_30d": [4.8, 5.1],
            "team_rs_season": [4.5, 5.0],
            "opp_ra_30d": [4.2, 4.0],
            "is_home": [1, 0],
            "is_coors": [1, 0],
        }
    )
    model = RunsBaseline().fit(train)
    pred = model.predict(frame)
    assert pred.shape == (2,)
    assert np.all(pred >= 0.5)
    assert pred[0] > pred[1]  # home + coors bump
