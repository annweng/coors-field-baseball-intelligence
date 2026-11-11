"""Model evaluation endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

router = APIRouter()

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ACTIVE_PA = _REPO_ROOT / "models" / "artifacts" / "active_model.json"
_ACTIVE_RUNS = _REPO_ROOT / "models" / "artifacts" / "active_runs_model.json"
_REPORT_DIR = _REPO_ROOT / "data" / "cache" / "reports"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _metrics_test_log_loss(metrics: Any) -> float | None:
    if not isinstance(metrics, dict):
        return None
    test = metrics.get("test")
    if isinstance(test, dict) and test.get("log_loss") is not None:
        return float(test["log_loss"])
    if metrics.get("log_loss") is not None:
        return float(metrics["log_loss"])
    return None


def _metrics_beats_baseline(metrics: Any) -> bool | None:
    if not isinstance(metrics, dict):
        return None
    if metrics.get("beats_baseline_log_loss") is not None:
        return bool(metrics["beats_baseline_log_loss"])
    return None


def _metrics_baseline_ll(metrics: Any) -> float | None:
    if not isinstance(metrics, dict):
        return None
    base = metrics.get("baseline_on_same_test")
    if isinstance(base, dict) and base.get("log_loss") is not None:
        return float(base["log_loss"])
    return None


@router.get("/models/active")
def active_models() -> dict:
    pa_meta = _read_json(_ACTIVE_PA)
    runs_meta = _read_json(_ACTIVE_RUNS)
    version = pa_meta.get("model_version", "xgb-v0.2.2")
    report_path = _REPORT_DIR / f"model-eval-{version}.json"
    report = _read_json(report_path)
    test_block = report.get("test") if isinstance(report.get("test"), dict) else {}
    return {
        "plate_appearance": {
            **pa_meta,
            "calibration_k": test_block.get("calibration_k"),
            "calibration_hr": test_block.get("calibration_hr"),
            "test_n": test_block.get("n"),
            "player_game": test_block.get("player_game"),
        },
        "runs": runs_meta,
    }


@router.get("/models/evaluations/latest")
def latest_evaluations() -> dict:
    try:
        conn_ctx = engine.connect()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database_unavailable: {exc}") from exc

    with conn_ctx as conn:
        rows = conn.execute(
            text(
                """
                SELECT model_version, evaluation_type, train_end, test_end, metrics, created_at
                FROM model_evaluations
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
        ).mappings().all()
    return {
        "evaluations": [
            {
                "model_version": r["model_version"],
                "evaluation_type": r["evaluation_type"],
                "train_end": str(r["train_end"]) if r["train_end"] else None,
                "test_end": str(r["test_end"]) if r["test_end"] else None,
                "test_log_loss": _metrics_test_log_loss(r["metrics"]),
                "beats_baseline": _metrics_beats_baseline(r["metrics"]),
                "baseline_log_loss": _metrics_baseline_ll(r["metrics"]),
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }
