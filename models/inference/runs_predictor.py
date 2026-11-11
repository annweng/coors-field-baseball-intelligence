"""Team run expectancy inference."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from data_pipeline.runs.team_games import build_team_game_dataset
from models.runs.features import encode_matrix

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_RUNS = ROOT / "models" / "artifacts" / "active_runs_model.json"
DEFAULT_ARTIFACT = ROOT / "models" / "artifacts" / "runs-v0.1.0.joblib"


class RunsPredictor:
    def __init__(self) -> None:
        meta = json.loads(ACTIVE_RUNS.read_text(encoding="utf-8")) if ACTIVE_RUNS.exists() else {}
        path = ROOT / "models" / "artifacts" / meta.get("artifact", DEFAULT_ARTIFACT.name)
        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.baseline = bundle["baseline"]
        self.feature_columns = bundle["feature_columns"]
        self.model_version = bundle.get("model_version", path.stem)
        self.use_ridge = bool(meta.get("beats_baseline"))

    def _latest_team_row(self, frame: pd.DataFrame, team_id: int) -> pd.Series:
        sub = frame[frame["team_id"] == team_id]
        if sub.empty:
            raise ValueError(f"No team-game history for team {team_id}")
        return sub.sort_values("game_date").iloc[-1]

    def predict_matchup(
        self,
        *,
        home_team_id: int,
        away_team_id: int,
        season: int = 2024,
    ) -> dict:
        featured = build_team_game_dataset(seasons=list(range(2021, season + 1)))
        home_row = self._latest_team_row(featured, home_team_id).copy()
        away_row = self._latest_team_row(featured, away_team_id).copy()

        home_row["is_home"] = 1
        home_row["opponent_id"] = away_team_id
        home_row["opp_rs_30d"] = away_row["team_rs_30d"]
        home_row["opp_ra_30d"] = away_row["team_ra_30d"]

        away_row["is_home"] = 0
        away_row["opponent_id"] = home_team_id
        away_row["opp_rs_30d"] = home_row["team_rs_30d"]
        away_row["opp_ra_30d"] = home_row["team_ra_30d"]
        away_row["stadium_id"] = home_row["stadium_id"]
        away_row["is_coors"] = home_row["is_coors"]

        rows = pd.DataFrame([home_row, away_row])
        if self.use_ridge:
            x, _ = encode_matrix(rows)
            pred_arr = np.maximum(0.5, self.model.predict(x))
        else:
            pred_arr = np.asarray(self.baseline.predict(rows), dtype=float)

        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "season": season,
            "expected_runs_home": float(pred_arr[0]),
            "expected_runs_away": float(pred_arr[1]),
            "expected_total_runs": float(pred_arr[0] + pred_arr[1]),
            "model_version": self.model_version,
            "production_model": "ridge" if self.use_ridge else "baseline",
        }
