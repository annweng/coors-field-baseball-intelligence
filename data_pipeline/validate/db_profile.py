"""PostgreSQL dataset snapshots for documentation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def postgres_dataset_snapshot(session: Session) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    snap["plate_appearances_total"] = session.execute(
        text("SELECT COUNT(*) FROM plate_appearances")
    ).scalar_one()
    snap["teams"] = session.execute(text("SELECT COUNT(*) FROM teams")).scalar_one()
    snap["players"] = session.execute(text("SELECT COUNT(*) FROM players")).scalar_one()
    snap["games"] = session.execute(text("SELECT COUNT(*) FROM games")).scalar_one()

    by_season = session.execute(
        text(
            """
            SELECT g.season, COUNT(*) AS pas,
                   MIN(pa.game_date) AS min_date, MAX(pa.game_date) AS max_date
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            GROUP BY g.season ORDER BY g.season
            """
        )
    ).mappings().all()
    snap["plate_appearances_by_season"] = [dict(row) for row in by_season]

    outcomes = session.execute(
        text(
            """
            SELECT outcome::text AS outcome, COUNT(*) AS n
            FROM plate_appearances
            GROUP BY outcome ORDER BY outcome
            """
        )
    ).mappings().all()
    snap["outcome_distribution_db"] = {row["outcome"]: row["n"] for row in outcomes}

    coors = session.execute(
        text(
            """
            SELECT COUNT(*) FROM plate_appearances pa
            JOIN stadiums s ON s.stadium_id = pa.stadium_id
            WHERE s.is_coors_field = TRUE
            """
        )
    ).scalar_one()
    snap["coors_field_plate_appearances_db"] = coors
    return snap
