import { useEffect, useState } from "react";
import { fetchRunsForecast, fetchTeams } from "../lib/api";

export default function RunsPage() {
  const [teams, setTeams] = useState<Array<{ mlb_team_id: number; name: string }>>([]);
  const [homeId, setHomeId] = useState("");
  const [awayId, setAwayId] = useState("");
  const [result, setResult] = useState<Awaited<ReturnType<typeof fetchRunsForecast>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTeams()
      .then((r) => setTeams(r.teams.sort((a, b) => a.name.localeCompare(b.name))))
      .catch(() => setTeams([]));
  }, []);

  const teamName = (id: number) => teams.find((t) => t.mlb_team_id === id)?.name ?? String(id);

  const onRun = async () => {
    const home = Number(homeId);
    const away = Number(awayId);
    if (!home || !away || home === away) {
      setError("Pick two different teams.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchRunsForecast({ home_team_id: home, away_team_id: away, season: 2024 }));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Forecast failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-semibold text-white">Run Forecasting</h2>
      <p className="text-sm text-slate-400 leading-relaxed">
        Expected runs for a hypothetical matchup using trailing 30-day team offense and defense
        (2021–2024 scores in Postgres). Ridge model ships when holdout MAE beats the naive baseline;
        otherwise the API serves the baseline blend.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm text-slate-300">
          Home team
          <select
            className="mt-1 w-full rounded border border-navy-700 bg-navy-800 px-3 py-2 text-white"
            value={homeId}
            onChange={(e) => setHomeId(e.target.value)}
          >
            <option value="">Select…</option>
            {teams.map((t) => (
              <option key={t.mlb_team_id} value={t.mlb_team_id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-300">
          Away team
          <select
            className="mt-1 w-full rounded border border-navy-700 bg-navy-800 px-3 py-2 text-white"
            value={awayId}
            onChange={(e) => setAwayId(e.target.value)}
          >
            <option value="">Select…</option>
            {teams.map((t) => (
              <option key={t.mlb_team_id} value={t.mlb_team_id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <button
        type="button"
        disabled={loading}
        onClick={onRun}
        className="rounded bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-purple disabled:opacity-50"
      >
        {loading ? "Running…" : "Estimate runs"}
      </button>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      {result ? (
        <div className="rounded-lg border border-navy-700 bg-navy-900/60 p-4 text-sm space-y-2">
          <p className="font-semibold text-white">
            {teamName(result.home_team_id)} (home) vs {teamName(result.away_team_id)} (away)
          </p>
          <p className="text-slate-400">
            Model: {result.model_version} ({result.production_model})
          </p>
          <ul className="space-y-1 text-slate-200">
            <li className="flex justify-between">
              <span>Home runs</span>
              <span>{result.expected_runs_home.toFixed(2)}</span>
            </li>
            <li className="flex justify-between">
              <span>Away runs</span>
              <span>{result.expected_runs_away.toFixed(2)}</span>
            </li>
            <li className="flex justify-between font-medium text-white">
              <span>Total</span>
              <span>{result.expected_total_runs.toFixed(2)}</span>
            </li>
          </ul>
        </div>
      ) : null}
    </div>
  );
}
