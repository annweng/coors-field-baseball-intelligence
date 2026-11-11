import { useState } from "react";
import {
  fetchPlayerAvailability,
  fetchPlayerForecast,
  fetchPlayerSummary,
  searchPlayers,
} from "../lib/api";

const OUTCOME_LABELS: Record<string, string> = {
  strikeout: "Strikeout",
  walk: "Walk",
  hit_by_pitch: "Hit by pitch",
  single: "Single",
  double: "Double",
  triple: "Triple",
  home_run: "Home run",
  other_out: "Other out (groundout, flyout, etc.)",
};

export default function ForecastsPage() {
  const [season, setSeason] = useState(2024);
  const [batterQuery, setBatterQuery] = useState("");
  const [pitcherQuery, setPitcherQuery] = useState("");
  const [batterResults, setBatterResults] = useState<Array<{ mlb_player_id: number; full_name: string }>>([]);
  const [pitcherResults, setPitcherResults] = useState<Array<{ mlb_player_id: number; full_name: string }>>([]);
  const [batterId, setBatterId] = useState<number | null>(null);
  const [batterName, setBatterName] = useState("");
  const [pitcherId, setPitcherId] = useState<number | null>(null);
  const [pitcherName, setPitcherName] = useState("");
  const [batterPa, setBatterPa] = useState<number | null>(null);
  const [pitcherPa, setPitcherPa] = useState<number | null>(null);
  const [stadiumCoors, setStadiumCoors] = useState(false);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [forecast, setForecast] = useState<Awaited<ReturnType<typeof fetchPlayerForecast>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchingBatter, setSearchingBatter] = useState(false);
  const [searchingPitcher, setSearchingPitcher] = useState(false);

  const onSearchBatter = async () => {
    if (batterQuery.length < 2) return;
    setSearchingBatter(true);
    setError(null);
    try {
      const res = await searchPlayers(batterQuery);
      setBatterResults(res.players);
      if (res.players.length === 0) {
        setError("No players found — try last name only, then click Search.");
      }
    } catch (e) {
      setBatterResults([]);
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearchingBatter(false);
    }
  };

  const onSearchPitcher = async () => {
    if (pitcherQuery.length < 2) return;
    setSearchingPitcher(true);
    setError(null);
    try {
      const res = await searchPlayers(pitcherQuery);
      setPitcherResults(res.players);
      if (res.players.length === 0) {
        setError("No pitchers found — try last name only, then click Search.");
      }
    } catch (e) {
      setPitcherResults([]);
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearchingPitcher(false);
    }
  };

  const onSelectBatter = async (id: number, name: string) => {
    setBatterId(id);
    setBatterName(name);
    setForecast(null);
    setError(null);
    setSummary(null);
    try {
      const avail = await fetchPlayerAvailability(id, season);
      setBatterPa(avail.pa_as_batter);
      if (!avail.forecast_ok_batter) {
        setError(
          `${name} has no ${season} batting data in this database. Try another season or load that year via ETL.`,
        );
        return;
      }
      setSummary(await fetchPlayerSummary(id, season));
    } catch (e) {
      setBatterPa(null);
      setError(e instanceof Error ? e.message : "Could not load batter stats");
    }
  };

  const onSelectPitcher = async (id: number, name: string) => {
    setPitcherId(id);
    setPitcherName(name);
    setForecast(null);
    setError(null);
    try {
      const avail = await fetchPlayerAvailability(id, season);
      setPitcherPa(avail.pa_as_pitcher);
      if (!avail.forecast_ok_pitcher) {
        setError(
          `${name} did not pitch in ${season} in this database (0 PAs as pitcher). ` +
            "Pick a starter/reliever — not a DH-only hitter like Ohtani in 2024.",
        );
      }
    } catch (e) {
      setPitcherPa(null);
      setError(e instanceof Error ? e.message : "Could not check pitcher");
    }
  };

  const canForecast =
    batterId != null &&
    pitcherId != null &&
    (batterPa ?? 0) > 0 &&
    (pitcherPa ?? 0) > 0;

  const onRunForecast = async () => {
    if (!batterId || !pitcherId) {
      setError("Select a batter and a pitcher.");
      return;
    }
    if (!canForecast) {
      setError("Batter and pitcher both need plate appearances in the selected season.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPlayerForecast({
        batter_id: batterId,
        pitcher_id: pitcherId,
        stadium_id: stadiumCoors ? 19 : undefined,
        season,
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
        Hypothetical plate appearance: batter rolling rates vs pitcher rolling rates for the season
        you choose (must exist in Postgres).
      </p>

      <label className="text-sm text-slate-300">
        Season
        <select
          className="mt-1 block rounded border border-navy-700 bg-navy-800 px-3 py-2 text-white"
          value={season}
          onChange={(e) => {
            setSeason(Number(e.target.value));
            setBatterId(null);
            setPitcherId(null);
            setSummary(null);
            setBatterPa(null);
            setPitcherPa(null);
            setForecast(null);
          }}
        >
          {[2021, 2022, 2023, 2024, 2025].map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>

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
          disabled={searchingBatter}
          className="rounded bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-purple disabled:opacity-50"
        >
          {searchingBatter ? "…" : "Search"}
        </button>
      </div>

      <ul className="divide-y divide-navy-700 rounded-lg border border-navy-700 max-h-40 overflow-y-auto">
        {batterResults.length === 0 && !searchingBatter ? (
          <li className="px-4 py-3 text-slate-500 text-sm">Search results appear here.</li>
        ) : null}
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
          <p className="font-semibold text-white">
            {String(summary.full_name)} — {season} batter ({batterPa?.toLocaleString()} PAs)
          </p>
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
          disabled={searchingPitcher}
          className="rounded bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-purple disabled:opacity-50"
        >
          {searchingPitcher ? "…" : "Search"}
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

      {pitcherId ? (
        <p className="text-sm text-slate-400">
          {pitcherName}: {pitcherPa != null ? `${pitcherPa.toLocaleString()} PAs as pitcher in ${season}` : "…"}
        </p>
      ) : null}

      <div className="rounded-lg border border-navy-700 bg-navy-900/40 p-4 space-y-3">
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
          disabled={loading || !canForecast}
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
            {stadiumCoors ? " @ Coors" : ""} ({season})
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
