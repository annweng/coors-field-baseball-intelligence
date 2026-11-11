# Roadmap notes

## Product A (polish) — done

- `/models/active` with calibration series for Model Lab
- Overview + Model Lab copy aligned with `xgb-v0.2.2`
- Player Forecasts: batter and pitcher name search

## Milestone 8 — run forecasting

1. `games.home_score` / `away_score` via MLB schedule + `sync-scores`
2. `models/train_runs.py` → `runs-v0.1.0`, `active_runs_model.json`
3. `GET /api/v1/forecasts/runs` + Run Forecasting UI

Train: `.\scripts\sync-scores.ps1` then `.\scripts\train_runs.ps1`

## Deferred: advanced PA retraining (reference)

Milestones 6–7 (Coors lab + full UI) ship first. **Return to modeling** afterward:

1. Train **XGBoost** in Docker (Python 3.12) — not available on host Python 3.14.
2. Align **chronological test window** with baseline for fair log-loss comparison.
3. Retune **calibration** (validation window, method).
4. Export calibration plots for Model Lab UI.
5. Wire **Player Forecasts** to live inference once holdout beats baseline.

Track eval artifacts: `baseline-v0.1.0`, `gbm-v0.1.0`, `xgb-v0.2.0`, `xgb-v0.2.1` in `model_evaluations`.

### Retrain status (2024 holdout through 2024-10-31)

| Model | Test log loss | vs baseline (2.221) |
|-------|---------------|---------------------|
| `xgb-v0.2.0` (calibrated) | 2.976 | Worse |
| `xgb-v0.2.1` (no calibration) | 2.964 | Worse |
| `xgb-v0.2.2` (baseline stack + class weights) | **2.103** | **Beats baseline** |

**Train:** `.\scripts\train_xgb.ps1` (Docker + `host.docker.internal:5433`).

**Live API:** `/api/v1/forecasts/player` serves **XGB** when `active_model.json` has `beats_baseline: true` (currently `xgb-v0.2.2`).

### Next tuning ideas

- Class weights / focal loss for rare outcomes (3B, HBP)
- Monotone or selective feature sets; pitcher–batter interaction terms
- Separate calibration on 2024-only validation
- Player-game loss as training objective (not only PA log loss)
