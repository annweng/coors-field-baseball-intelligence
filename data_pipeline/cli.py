"""CLI for ingestion, validation, and load."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from data_pipeline.ingest.statcast import fetch_season, load_cached_meta
from data_pipeline.load.postgres import (
    create_session,
    ensure_teams,
    load_plate_appearances,
    record_etl_run,
    sync_mlb_metadata,
)
from data_pipeline.settings import settings
from data_pipeline.transform.plate_appearances import pitches_to_plate_appearances
from data_pipeline.validate.dataset_doc import write_dataset_doc
from data_pipeline.validate.db_profile import postgres_dataset_snapshot
from data_pipeline.validate.profile import build_season_profile, merge_profiles
from data_pipeline.validate.quality import build_quality_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("data_pipeline")


def _normalize_pitches(df):
    import pandas as pd

    if "des" in df.columns and "description" not in df.columns:
        df = df.rename(columns={"des": "description"})
    return df


def cmd_sync_player_names(args: argparse.Namespace) -> None:
    from data_pipeline.load.postgres import sync_player_names

    session = create_session(settings.database_url)
    try:
        stats = sync_player_names(session)
        record_etl_run(session, "sync_player_names", None, "success", None, stats)
        logger.info("Synced player names: %s", stats)
    finally:
        session.close()


def cmd_sync_scores(args: argparse.Namespace) -> None:
    session = create_session(settings.database_url)
    try:
        total = 0
        for season in args.seasons:
            stats = sync_mlb_metadata(session, season)
            total += stats.get("games", 0)
            logger.info("Season %s scores synced (%s games)", season, stats.get("games", 0))
        record_etl_run(session, "sync_scores", None, "success", None, {"games": total})
    finally:
        session.close()


def cmd_sync_metadata(args: argparse.Namespace) -> None:
    session = create_session(settings.database_url)
    try:
        stats = sync_mlb_metadata(session, args.season)
        record_etl_run(session, "mlb_metadata", args.season, "success", None, stats)
        logger.info("Synced metadata: %s", stats)
    finally:
        session.close()


def cmd_ingest(args: argparse.Namespace) -> None:
    df = fetch_season(args.season, force=args.force)
    logger.info("Ingested %s pitch rows for season %s", len(df), args.season)
    meta = load_cached_meta(args.season)
    logger.info("Cached months: %s", len(meta))


def cmd_validate(args: argparse.Namespace) -> None:
    df = fetch_season(args.season, force=False)
    df = _normalize_pitches(df)
    pa = pitches_to_plate_appearances(df)
    report = build_quality_report(df, pa, season=args.season)
    out = settings.data_cache_dir / "reports" / f"quality-{args.season}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Quality report written to %s (passed=%s)", out, report.get("passed"))
    if args.strict and not report.get("passed"):
        sys.exit(1)


def cmd_load(args: argparse.Namespace) -> None:
    session = create_session(settings.database_url)
    try:
        ensure_teams(session)
        if args.sync_schedule:
            sync_mlb_metadata(session, args.season)
        team_map = ensure_teams(session)

        df = fetch_season(args.season, force=False)
        df = _normalize_pitches(df)
        if df.empty:
            logger.error("No cached pitches for season %s — run ingest first", args.season)
            sys.exit(1)

        pa = pitches_to_plate_appearances(df)
        report = build_quality_report(df, pa, season=args.season)
        loaded = load_plate_appearances(session, pa, team_abbrev_map=team_map)
        record_etl_run(
            session,
            "statcast_load",
            args.season,
            "success",
            loaded,
            {"quality_passed": report.get("passed"), "plate_appearances": len(pa)},
        )
        out = settings.data_cache_dir / "reports" / f"quality-{args.season}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Loaded %s plate appearances", loaded)
    finally:
        session.close()


def _db_seasons_loaded(session) -> set[int]:
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT DISTINCT g.season
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            """
        )
    ).scalars()
    return set(rows)


def cmd_profile_dataset(args: argparse.Namespace) -> None:
    profiles: list[dict] = []
    db_seasons: set[int] = set()
    if not args.skip_db:
        session = create_session(settings.database_url)
        try:
            db_seasons = _db_seasons_loaded(session)
        finally:
            session.close()

    for season in args.seasons:
        df = fetch_season(season, force=False)
        if df.empty:
            logger.warning("No cache for season %s", season)
            continue
        df = _normalize_pitches(df)
        profiles.append(
            build_season_profile(df, season=season, in_database=(season in db_seasons))
        )

    merged = merge_profiles(profiles)
    out = settings.data_cache_dir / "reports" / "dataset-profile.json"
    out.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    postgres = None
    if not args.skip_db:
        session = create_session(settings.database_url)
        try:
            postgres = postgres_dataset_snapshot(session)
        finally:
            session.close()

    doc_path = REPO_ROOT / "docs" / "dataset-2021-2025.md"
    write_dataset_doc(merged, doc_path, postgres=postgres)
    logger.info("Wrote %s and %s", out, doc_path)


def cmd_pipeline(args: argparse.Namespace) -> None:
    """ingest → validate → load in one invocation."""
    args.sync_schedule = True
    cmd_ingest(args)
    cmd_load(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coors Field BI data pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync-metadata", help="Sync MLB teams, venues, and schedule")
    sync.add_argument("--season", type=int, required=True)
    sync.set_defaults(func=cmd_sync_metadata)

    names = sub.add_parser("sync-player-names", help="Refresh player names from MLB Stats API")
    names.set_defaults(func=cmd_sync_player_names)

    scores = sub.add_parser("sync-scores", help="Refresh schedule + final scores for seasons")
    scores.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        default=[2021, 2022, 2023, 2024, 2025],
    )
    scores.set_defaults(func=cmd_sync_scores)

    ingest = sub.add_parser("ingest", help="Download/cache Statcast for a season")
    ingest.add_argument("--season", type=int, required=True)
    ingest.add_argument("--force", action="store_true")
    ingest.set_defaults(func=cmd_ingest)

    validate = sub.add_parser("validate", help="Build data quality report from cache")
    validate.add_argument("--season", type=int, required=True)
    validate.add_argument("--strict", action="store_true")
    validate.set_defaults(func=cmd_validate)

    load = sub.add_parser("load", help="Load cached season into PostgreSQL")
    load.add_argument("--season", type=int, required=True)
    load.add_argument("--sync-schedule", action="store_true", default=True)
    load.set_defaults(func=cmd_load)

    pipe = sub.add_parser("run", help="Full ingest + load for a season")
    pipe.add_argument("--season", type=int, required=True)
    pipe.add_argument("--force", action="store_true")
    pipe.set_defaults(func=cmd_pipeline)

    prof = sub.add_parser("profile-dataset", help="Build dataset doc for seasons (cache)")
    prof.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        default=[2021, 2022, 2023, 2024, 2025],
    )
    prof.add_argument("--skip-db", action="store_true")
    prof.set_defaults(func=cmd_profile_dataset)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
