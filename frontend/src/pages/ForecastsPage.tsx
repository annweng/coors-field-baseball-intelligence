import { useState } from "react";
import { fetchPlayerForecast, fetchPlayerSummary, searchPlayers } from "../lib/api";

const OUTCOME_LABELS: Record<string, string> = {
  strikeout: "K",
  walk: "BB",
  hit_by_pitch: "HBP",
  single: "1B",
  double: "2B",
  triple: "3B",
  home_run: "HR",
  other_out: "Out (other)",
};

export default function ForecastsPage() {
  const [batterQuery, setBatterQuery] = useState("");
  const [pitcherQuery, setPitcherQuery] = useState("");
  const [batterResults, setBatterResults] = useState<Array<{ mlb_player_id: number; full_name: string }>>([]);
  const [pitcherResults, setPitcherResults] = useState<Array<{ mlb_player_id: number; full_name: string }>>([]);
  const [batterId, setBatterId] = useState<number | null>(null);
  const [batterName, setBatterName] = useState("");
  const [pitcherId, setPitcherId] = useState<number | null>(null);
  const [pitcherName, setPitcherName] = useState("");
  const [stadiumCoors, setStadiumCoors] = useState(false);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [forecast, setForecast] = useState<Awaited<ReturnType<typeof fetchPlayerForecast>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSearchBatter = async () => {
    if (batterQuery.length < 2) return;
    setBatterResults((await searchPlayers(batterQuery)).players);
  };

  const onSearchPitcher = async () => {
    if (pitcherQuery.length < 2) return;
    setPitcherResults((await searchPlayers(pitcherQuery)).players);
  };

  const onSelectBatter = async (id: number, name: string) => {
    setBatterId(id);
    setBatterName(name);
    setForecast(null);
    setError(null);
    setSummary(await fetchPlayerSummary(id, 2024));
  };

  const onSelectPitcher = (id: number, name: string) => {
    setPitcherId(id);
    setPitcherName(name);
    setForecast(null);
    setError(null);
  };

  const onRunForecast = async () => {
    if (!batterId || !pitcherId) {
      setError("Select a batter and a pitcher.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPlayerForecast({
        batter_id: batterId,
        pitcher_id: pitcherId,
        stadium_id: stadiumCoors ? 19 : undefined,
        season: 2024,
      });
      setForecast(res);
    } catch (e) {
      setForecast(null);
      setError(e instanceof Error ? e.message : "Forecast failed");
    } finally {
      setLoading(false);
    }
  };

  const probs = forecast?.outcome_probabilities
    ? Object.entries(forecast.outcome_probabilities).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-semibold text-white">Player Forecasts</h2>
      <p className="text-sm text-slate-400">
        Multiclass PA outcome probabilities from the active model (see Model Lab). Uses 2024 rolling
        features for batter and pitcher.
      </p>

      <p className="text-sm font-medium text-white">Batter</p>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-navy-700 bg-navy-800 px-3 py-2 text-white"
          placeholder="Search batter name"
          value={batterQuery}
          onChange={(e) => setBatterQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearchBatter()}
        />
        <button
          type="button"
          onClick={onSearchBatter}
          className="rounded bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-purple"
        >
          Search
        </button>
      </div>

      <ul className="divide-y divide-navy-700 rounded-lg border border-navy-700 max-h-40 overflow-y-auto">
        {batterResults.map((p) => (
          <li key={p.mlb_player_id}>
            <button
              type="button"
              onClick={() => onSelectBatter(p.mlb_player_id, p.full_name)}
              className={`w-full text-left px-4 py-2 hover:bg-navy-800 ${
                batterId === p.mlb_player_id ? "bg-navy-800 text-white" : "text-slate-200"
              }`}
            >
              {p.full_name}
            </button>
          </li>
        ))}
      </ul>

      {summary && batterId ? (
        <div className="rounded-lg border border-navy-700 bg-navy-900/60 p-4 text-sm space-y-1">
          <p className="font-semibold text-white">{String(summary.full_name)} — 2024 batter</p>
          <p>PA: {Number(summary.pa).toLocaleString()}</p>
          <p>HR rate: {(Number(summary.hr_rate) * 100).toFixed(2)}%</p>
          <p>K rate: {(Number(summary.k_rate) * 100).toFixed(2)}%</p>
          <p>BB rate: {(Number(summary.bb_rate) * 100).toFixed(2)}%</p>
        </div>
      ) : null}

      <p className="text-sm font-medium text-white">Pitcher</p>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-navy-700 bg-navy-800 px-3 py-2 text-white"
          placeholder="Search pitcher name"
          value={pitcherQuery}
          onChange={(e) => setPitcherQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearchPitcher()}
        />
        <button
          type="button"
          onClick={onSearchPitcher}
          className="rounded bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-purple"
        >
          Search
        </button>
      </div>

      <ul className="divide-y divide-navy-700 rounded-lg border border-navy-700 max-h-40 overflow-y-auto">
        {pitcherResults.map((p) => (
          <li key={p.mlb_player_id}>
            <button
              type="button"
              onClick={() => onSelectPitcher(p.mlb_player_id, p.full_name)}
              className={`w-full text-left px-4 py-2 hover:bg-navy-800 ${
                pitcherId === p.mlb_player_id ? "bg-navy-800 text-white" : "text-slate-200"
              }`}
            >
              {p.full_name}
            </button>
          </li>
        ))}
      </ul>

      <div className="rounded-lg border border-navy-700 bg-navy-900/40 p-4 space-y-3">
        <p className="text-sm text-slate-300">
          {pitcherId ? `Pitcher: ${pitcherName} (${pitcherId})` : "Select a pitcher above."}
        </p>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={stadiumCoors}
            onChange={(e) => setStadiumCoors(e.target.checked)}
          />
          Play at Coors Field
        </label>
        <button
          type="button"
          disabled={loading || !batterId || !pitcherId}
          onClick={onRunForecast}
          className="rounded bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-purple disabled:opacity-50"
        >
          {loading ? "Running…" : "Run forecast"}
        </button>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
      </div>

      {forecast ? (
        <div className="rounded-lg border border-navy-700 bg-navy-900/60 p-4 text-sm space-y-2">
          <p className="font-semibold text-white">
            {batterName} vs {pitcherName}
            {stadiumCoors ? " @ Coors" : ""}
          </p>
          <p className="text-slate-400">
            Model: {forecast.model_version} ({forecast.production_model})
          </p>
          <ul className="space-y-1">
            {probs.map(([k, v]) => (
              <li key={k} className="flex justify-between text-slate-200">
                <span>{OUTCOME_LABELS[k] ?? k}</span>
                <span>{(v * 100).toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
