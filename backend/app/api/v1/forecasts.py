"""Player PA outcome forecasts."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["forecasts"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
ACTIVE_MODEL = _REPO_ROOT / "models" / "artifacts" / "active_model.json"


def _ensure_repo_path() -> None:
    import sys

    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


def _active_meta() -> dict:
    if not ACTIVE_MODEL.exists():
        return {}
    try:
        return json.loads(ACTIVE_MODEL.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


@router.get("/forecasts/player")
def player_forecast(
    batter_id: int = Query(..., ge=1),
    pitcher_id: int = Query(..., ge=1),
    stadium_id: int | None = Query(None),
    season: int = Query(2024, ge=2021, le=2025),
) -> dict:
    _ensure_repo_path()
    meta = _active_meta()
    model_used = "baseline-v0.1.0"

    try:
        if meta.get("beats_baseline"):
            from models.inference.predictor import PaOutcomePredictor

            predictor = PaOutcomePredictor()
            probs = predictor.predict_matchup(
                batter_id=batter_id,
                pitcher_id=pitcher_id,
                stadium_id=stadium_id,
                as_of_season=season,
            )
            model_used = predictor.model_version
        else:
            from models.inference.baseline_api import baseline_matchup_probabilities

            probs = baseline_matchup_probabilities(
                batter_id=batter_id,
                pitcher_id=pitcher_id,
                stadium_id=stadium_id,
                as_of_season=season,
            )
    except FileNotFoundError as exc:
        from models.inference.baseline_api import baseline_matchup_probabilities

        probs = baseline_matchup_probabilities(
            batter_id=batter_id,
            pitcher_id=pitcher_id,
            stadium_id=stadium_id,
            as_of_season=season,
        )
        model_used = "baseline-v0.1.0"
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"inference_error: {exc}") from exc

    return {
        "model_version": model_used,
        "production_model": "xgb" if meta.get("beats_baseline") else "baseline",
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "stadium_id": stadium_id,
        "season": season,
        "outcome_probabilities": probs,
        "probability_sum": round(sum(probs.values()), 6),
        "note": None
        if meta.get("beats_baseline")
        else "Baseline active until XGB holdout beats baseline (see docs/ROADMAP.md).",
    }


@router.get("/forecasts/runs")
def runs_forecast(
    home_team_id: int = Query(..., ge=1),
    away_team_id: int = Query(..., ge=1),
    season: int = Query(2024, ge=2021, le=2025),
) -> dict:
    _ensure_repo_path()
    active_runs = _REPO_ROOT / "models" / "artifacts" / "active_runs_model.json"
    if not active_runs.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "run_model_missing",
                "message": "Train runs model: python -m models.train_runs (after sync-scores).",
            },
        )
    try:
        from models.inference.runs_predictor import RunsPredictor

        result = RunsPredictor().predict_matchup(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            season=season,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"inference_error: {exc}") from exc
    return result
