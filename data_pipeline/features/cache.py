"""Persist expensive rolling-feature frames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_pipeline.features.rolling import build_rolling_features
from data_pipeline.settings import settings


def features_cache_path(season: int) -> Path:
    return settings.data_cache_dir / "features" / f"pa_features_{season}.parquet"


def load_or_build_features(pa: pd.DataFrame, *, season: int, force: bool = False) -> pd.DataFrame:
    path = features_cache_path(season)
    if path.exists() and not force:
        return pd.read_parquet(path)
    featured = build_rolling_features(pa)
    path.parent.mkdir(parents=True, exist_ok=True)
    featured.to_parquet(path, index=False)
    return featured
