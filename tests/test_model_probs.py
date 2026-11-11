import numpy as np

from models.evaluation.metrics import evaluate_multiclass


def test_evaluate_multiclass_probabilities_sum():
    labels = ["strikeout", "walk", "hit_by_pitch", "single", "double", "triple", "home_run", "other_out"]
    y = ["single", "strikeout"]
    p = np.array(
        [
            [0.1, 0.1, 0.05, 0.4, 0.1, 0.05, 0.1, 0.1],
            [0.5, 0.1, 0.05, 0.05, 0.05, 0.05, 0.1, 0.1],
        ]
    )
    m = evaluate_multiclass(y, p)
    assert m["n"] == 2
    assert 0.0 <= m["log_loss"] < 10
