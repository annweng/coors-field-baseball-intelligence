# Data sources and access limitations

## Verified on Milestone 1 (2025-11-11, environment: Windows)

| Check | Result |
|-------|--------|
| `https://statsapi.mlb.com/api/v1/teams?sportId=1` | HTTP 200 |
| `pybaseball.statcast('2024-04-01','2024-04-02')` | ~7.8k pitch rows, 119 columns (~5s) |

## Statcast (primary)

**Access:** `pybaseball.statcast(start, end)` or Savant CSV endpoints.

**Limitations:**

- Large date ranges are slow and memory-heavy; use **chunked ingestion** (weekly or monthly) with disk cache.
- Occasional schema/column changes; pipeline must tolerate nullable new fields.
- Rate limiting / blocking possible under aggressive parallel downloads; backoff and respect terms of use.
- Not all historical fields exist for all seasons; 2021–2025 is the stated scope.

## MLB Stats API

**Access:** Public REST, no key required for read endpoints.

**Limitations:**

- Game logs and rosters may need pagination.
- IDs must be stored as canonical keys (`mlb_player_id`, `team_id`, `game_pk`).

## FanGraphs

**Access:** Often via `pybaseball` scraping helpers.

**Limitations:**

- HTML structure changes can break scrapers; pin pybaseball version and add integration tests.
- Respect site terms; cache responses; do not hammer endpoints.

## Usage policy (project)

- No fabricated statistics in production UI.
- Cache retrieval timestamps in metadata tables or sidecar JSON.
- If ingest fails, show empty state + last successful sync time.
- Do not commit multi-GB raw dumps; use `data/cache/` (gitignored).

## Outcome taxonomy (planned)

Map Statcast `events` / `description` to training classes:

`strikeout`, `walk`, `hit_by_pitch`, `single`, `double`, `triple`, `home_run`, `other_out`

Document ambiguous cases (sacrifices, catcher's interference) in `docs/outcome-mapping.md` during Milestone 3.
