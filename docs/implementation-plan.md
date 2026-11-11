# Implementation plan

Work proceeds in verified milestones. Each milestone ends with a short report: what shipped, files touched, tests run, errors, and remaining gaps.

## Milestone 1 — Environment and repository

- [x] Inspect toolchain (Docker, Python, Node, git)
- [x] Verify MLB Stats API and sample Statcast pull via pybaseball
- [x] Initialize git repo and directory scaffold
- [x] Document architecture, data risks, and roadmap

## Milestone 2 — Ingestion and database

- [x] PostgreSQL schema (`database/init/001_schema.sql`)
- [x] SQLAlchemy models (`backend/app/db/`)
- [x] Statcast monthly ingest + parquet cache (`data_pipeline/ingest/statcast.py`)
- [x] MLB API sync for teams, venues, schedule (`data_pipeline/ingest/mlb_api.py`)
- [x] PA aggregation, outcome mapping, quality report
- [x] Bulk load into PostgreSQL (`data_pipeline/load/postgres.py`)
- [x] CLI: `sync-metadata`, `ingest`, `validate`, `load`, `run`
- [x] API `/api/v1/status` (DB row counts)
- [x] Full 2024 season load verified (Postgres port 5433)

## Milestone 3 — Dataset validation (current)

- [x] Extended season profiles (`profile-dataset` CLI)
- [x] PostgreSQL snapshot in dataset doc
- [x] `docs/dataset-2021-2025.md` (2024 complete; other seasons after ingest)
- [ ] Cache/DB coverage for 2021–2023, 2025 (`ingest` per season)

## Milestone 4 — Features and baseline model

- [x] Rolling features (`data_pipeline/features/rolling.py`, `docs/features.md`)
- [x] Leakage tests (`tests/test_feature_leakage.py`)
- [x] Baseline forecaster + chronological splits (`models/train_baseline.py`)
- [x] Metrics JSON + `model_evaluations` table
- [ ] Player-game MAE aggregation (Milestone 5)

## Milestone 5 — Advanced model

- [x] `models/train_advanced.py` (HistGradientBoosting + isotonic calibration; XGBoost in Docker/py3.12)
- [x] Feature cache, player-game MAE, calibration bins in eval JSON
- [x] Artifact `models/artifacts/gbm-v0.1.0.joblib`, `model_evaluations` row
- [x] API `GET /api/v1/models/evaluations/latest`
- [ ] Beat baseline on holdout (retune / XGBoost on py3.12)

## Milestone 6 — Coors Field research module

- [x] `backend/app/services/coors.py` + `/api/v1/coors/*`
- [x] Park vs league, Rockies splits, trends, HR stadium leaderboard
- [x] Descriptive disclaimers in API + UI

## Milestone 7 — Full stack UI

- [x] Vite + React + Tailwind, six routed pages
- [x] Coors Lab + Model Lab + Overview wired to live API
- [x] Player search / historical summary; forecasts gated (ROADMAP)
- [x] Run forecasting disabled per spec

**Deferred modeling:** see `docs/ROADMAP.md`.

## Milestone 8 — Run forecasting

- [x] `games.home_score` / `away_score`, `sync-scores` CLI
- [x] Team-game features, `runs-v0.1.0` Ridge + naive baseline
- [x] `GET /forecasts/runs` + Run Forecasting UI (production = ridge when holdout MAE beats baseline by 0.05)
- [ ] Tune ridge / features to clear MAE gate (current holdout ~2.46 MAE, baseline ~2.46)

## Milestone 9 — Hardening

- [x] Expanded pytest suite (`tests/`, `pyproject.toml`, `scripts/test.ps1`)
- [x] GitHub Actions CI (Python 3.12 + Postgres service, frontend build)
- [x] [docs/runbook.md](runbook.md) reproduction guide
- [x] README refresh + screenshot capture instructions (`docs/screenshots/`)
- [ ] Optional Cursor-hosted remote (on demand — use share skill)

## Recommended execution order (Product A first)

```text
M2 ingest → M3 validate → M4 baseline → M5 advanced → M7 UI (forecasts + model lab)
          ↘ M6 Coors API/UI in parallel once PAs exist
          ↘ M8 after player model evaluated
```

## Python runtime note

Host Python is **3.14**. Backend and pipeline **Docker images should use Python 3.12** for predictable wheels (XGBoost, psycopg, scientific stack) while allowing local 3.14 for light scripts where possible.
