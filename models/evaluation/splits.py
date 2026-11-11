"""Chronological dataset splits."""

from __future__ import annotations

from datetime import date

import pandas as pd


def chronological_split(
    df: pd.DataFrame,
    *,
    train_end: date,
    val_end: date,
    test_end: date | None = None,
    date_col: str = "game_date",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.to_datetime(df[date_col])
    train = df[dates <= pd.Timestamp(train_end)].copy()
    val = df[(dates > pd.Timestamp(train_end)) & (dates <= pd.Timestamp(val_end))].copy()
    test = df[dates > pd.Timestamp(val_end)].copy()
    if test_end is not None:
        test = test[pd.to_datetime(test[date_col]) <= pd.Timestamp(test_end)].copy()
    return train, val, test
