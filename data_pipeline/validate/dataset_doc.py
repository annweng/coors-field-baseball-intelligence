"""Generate docs/dataset-2021-2025.md from profile JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def render_dataset_markdown(
    merged: dict[str, Any],
    *,
    postgres: dict[str, Any] | None = None,
    target_seasons: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025),
) -> str:
    lines: list[str] = [
        "# Dataset profile (2021–2025)",
        "",
        f"_Generated {datetime.now(timezone.utc).date().isoformat()} UTC._",
        "",
        "Primary source: Statcast via `pybaseball`. Plate appearances are terminal-pitch ",
        "aggregates mapped to eight outcome classes (see `docs/etl.md`).",
        "",
        "## Coverage summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Seasons profiled (cache) | {', '.join(map(str, merged.get('seasons', []))) or '—'} |",
        f"| Aggregate pitch rows (profiled) | {merged.get('aggregate_pitch_rows', 0):,} |",
        f"| Aggregate PAs (profiled) | {merged.get('aggregate_plate_appearances', 0):,} |",
        f"| All quality gates passed | {merged.get('all_quality_passed', False)} |",
        "",
    ]

    for season in target_seasons:
        prof = merged.get("season_profiles", {}).get(str(season))
        lines.append(f"## Season {season}")
        lines.append("")
        if not prof:
            lines.append("_Not yet ingested to cache — run `python -m data_pipeline.cli ingest --season "
                         f"{season}`._")
            lines.append("")
            continue
        dr = prof.get("date_range", {})
        lines.extend(
            [
                f"- **Date range:** {dr.get('min', '—')} to {dr.get('max', '—')}",
                f"- **Pitch rows:** {prof.get('pitch_rows', 0):,}",
                f"- **Plate appearances:** {prof.get('plate_appearances', 0):,}",
                f"- **Games / batters / pitchers:** {prof.get('unique_games', '—')} / "
                f"{prof.get('unique_batters', '—')} / {prof.get('unique_pitchers', '—')}",
                f"- **Quality passed:** {prof.get('passed')}",
                f"- **Unknown outcomes:** {prof.get('unknown_outcome_count', 0)}",
                f"- **Coors Field PAs (venue id):** {prof.get('coors_field_plate_appearances', '—')}",
                f"- **In PostgreSQL:** {prof.get('loaded_in_postgres', 'unknown')}",
                "",
                "<details><summary>Outcome distribution</summary>",
                "",
                "```json",
                json.dumps(prof.get("outcome_distribution", {}), indent=2),
                "```",
                "",
                "</details>",
                "",
            ]
        )

    if postgres:
        lines.extend(
            [
                "## PostgreSQL snapshot",
                "",
                f"- Total plate appearances loaded: **{postgres.get('plate_appearances_total', 0):,}**",
                f"- Players: {postgres.get('players', 0):,} | Games: {postgres.get('games', 0):,}",
                f"- Coors Field PAs (stadium flag): {postgres.get('coors_field_plate_appearances_db', 0):,}",
                "",
                "**By season (loaded):**",
                "",
            ]
        )
        for row in postgres.get("plate_appearances_by_season", []):
            lines.append(
                f"- {row['season']}: {row['pas']:,} PAs ({row['min_date']} – {row['max_date']})"
            )
        lines.append("")

    lines.extend(
        [
            "## Known limitations",
            "",
            "- Rolling features for Milestone 4+ exclude `unknown` outcomes from training.",
            "- Nov/Dec Statcast pulls may be empty (offseason).",
            "- Multi-season training requires each season cached or loaded via ETL.",
            "",
        ]
    )
    return "\n".join(lines)


def write_dataset_doc(
    merged: dict[str, Any],
    path: Path,
    *,
    postgres: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dataset_markdown(merged, postgres=postgres), encoding="utf-8")
