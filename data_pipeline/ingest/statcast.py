"""Download and cache Statcast pitch data by month."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import os

import pandas as pd
from pybaseball import statcast
from pybaseball.cache import enable as enable_pybaseball_cache

from data_pipeline.settings import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("PYBASEBALL_CACHE", str(settings.pybaseball_cache))
settings.pybaseball_cache.mkdir(parents=True, exist_ok=True)
enable_pybaseball_cache()


def _month_ranges(season: int) -> list[tuple[date, date]]:
    """Month slices [start, end) covering March–December."""
    ranges: list[tuple[date, date]] = []
    cursor = date(season, 3, 1)
    end = date(season + 1, 1, 1)
    while cursor < end:
        if cursor.month == 12:
            nxt = date(season + 1, 1, 1)
        else:
            nxt = date(cursor.year, cursor.month + 1, 1)
        ranges.append((cursor, min(nxt, end)))
        cursor = nxt
    return ranges


def _cache_path(season: int, month_start: date) -> Path:
    return settings.statcast_cache_dir / str(season) / f"{month_start:%Y-%m}.parquet"


def _meta_path(parquet_path: Path) -> Path:
    return parquet_path.with_suffix(".json")


def fetch_month(season: int, month_start: date, month_end: date, *, force: bool = False) -> pd.DataFrame:
    path = _cache_path(season, month_start)
    meta = _meta_path(path)

    if path.exists() and meta.exists() and not force:
        logger.info("Loading cache %s", path.name)
        return pd.read_parquet(path)

    inclusive_end = month_end - timedelta(days=1)
    logger.info("Downloading Statcast %s to %s", month_start, inclusive_end)
    df = statcast(month_start.isoformat(), inclusive_end.isoformat())
    if df is None or df.empty:
        logger.warning("No rows for %s–%s", month_start, inclusive_end)
        return pd.DataFrame()

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    meta.write_text(
        json.dumps(
            {
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "start": month_start.isoformat(),
                "end": inclusive_end.isoformat(),
                "rows": len(df),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return df


def fetch_season(season: int, *, force: bool = False) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for month_start, month_end in _month_ranges(season):
        chunk = fetch_month(season, month_start, month_end, force=force)
        if not chunk.empty:
            frames.append(chunk)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_cached_meta(season: int) -> list[dict]:
    season_dir = settings.statcast_cache_dir / str(season)
    if not season_dir.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(season_dir.glob("*.json"))]
