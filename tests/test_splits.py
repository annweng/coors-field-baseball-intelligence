from datetime import date

import pandas as pd

from models.evaluation.splits import chronological_split


def test_chronological_split_respects_cutoffs() -> None:
    df = pd.DataFrame(
        {
            "game_date": pd.to_datetime(["2024-06-01", "2024-08-15", "2024-09-10"]),
            "x": [1, 2, 3],
        }
    )
    train, val, test = chronological_split(
        df,
        train_end=date(2024, 7, 31),
        val_end=date(2024, 8, 31),
        test_end=date(2024, 10, 31),
    )
    assert len(train) == 1
    assert len(val) == 1
    assert len(test) == 1
    assert train["x"].iloc[0] == 1
    assert test["x"].iloc[0] == 3
