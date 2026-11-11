const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function apiGet<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`);
  } catch {
    throw new Error(
      "Cannot reach API at port 8000. Run .\\scripts\\run-api.ps1 (Postgres on 5433).",
    );
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    if (typeof detail === "string") {
      throw new Error(detail);
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      throw new Error(String((detail as { message: string }).message));
    }
    throw new Error(detail?.message ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const fetchStatus = () =>
  apiGet<{ database: string; teams: number; plate_appearances: number }>("/status");

export type CalibrationPoint = {
  bin: number;
  mean_predicted: number;
  empirical_rate: number;
  count: number;
};

export const fetchActiveModels = () =>
  apiGet<{
    plate_appearance: {
      model_version?: string;
      beats_baseline?: boolean;
      test_log_loss?: number;
      baseline_log_loss?: number;
      calibration_k?: { outcome: string; points: CalibrationPoint[] };
      calibration_hr?: { outcome: string; points: CalibrationPoint[] };
      test_n?: number;
    };
    runs: {
      model_version?: string;
      beats_baseline?: boolean;
      test_mae?: number;
      baseline_mae?: number;
    };
  }>("/models/active");

export const fetchModelEvals = () =>
  apiGet<{
    evaluations: Array<{
      model_version: string;
      evaluation_type: string;
      test_log_loss: number | null;
      beats_baseline: boolean | null;
      baseline_log_loss: number | null;
      created_at: string | null;
    }>;
  }>("/models/evaluations/latest");

export const fetchCoorsSummary = (season?: number) =>
  apiGet<Record<string, unknown>>(season ? `/coors/summary?season=${season}` : "/coors/summary");

export const searchPlayers = (q: string) =>
  apiGet<{ players: Array<{ mlb_player_id: number; full_name: string }> }>(
    `/players/search?q=${encodeURIComponent(q)}`,
  );

export const fetchPlayerSummary = (id: number, season?: number) =>
  apiGet<Record<string, unknown>>(
    season ? `/players/${id}/summary?season=${season}` : `/players/${id}/summary`,
  );

export const fetchPlayerAvailability = (id: number, season: number = 2024) =>
  apiGet<{
    mlb_player_id: number;
    season: number;
    pa_as_batter: number;
    pa_as_pitcher: number;
    forecast_ok_batter: boolean;
    forecast_ok_pitcher: boolean;
  }>(`/players/${id}/availability?season=${season}`);

export const fetchTeams = () => apiGet<{ teams: Array<{ mlb_team_id: number; name: string }> }>("/teams");

export const fetchPlayerForecast = (params: {
  batter_id: number;
  pitcher_id: number;
  stadium_id?: number;
  season?: number;
}) => {
  const q = new URLSearchParams({
    batter_id: String(params.batter_id),
    pitcher_id: String(params.pitcher_id),
    season: String(params.season ?? 2024),
  });
  if (params.stadium_id != null) q.set("stadium_id", String(params.stadium_id));
  return apiGet<{
    model_version: string;
    production_model: string;
    outcome_probabilities: Record<string, number>;
    probability_sum: number;
    note: string | null;
  }>(`/forecasts/player?${q}`);
};

export const fetchRunsForecast = (params: {
  home_team_id: number;
  away_team_id: number;
  season?: number;
}) => {
  const q = new URLSearchParams({
    home_team_id: String(params.home_team_id),
    away_team_id: String(params.away_team_id),
    season: String(params.season ?? 2024),
  });
  return apiGet<{
    home_team_id: number;
    away_team_id: number;
    season: number;
    expected_runs_home: number;
    expected_runs_away: number;
    expected_total_runs: number;
    model_version: string;
    production_model: string;
  }>(`/forecasts/runs?${q}`);
};
