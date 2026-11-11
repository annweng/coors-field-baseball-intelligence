import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { StatCard } from "../components/StatCard";
import { fetchCoorsSummary } from "../lib/api";

type RateRow = {
  site?: string;
  season?: number;
  hr_rate?: number;
  hit_rate?: number;
  k_rate?: number;
  pa?: number;
  name?: string;
  stadium_id?: number;
  is_coors_field?: boolean;
};

type Factors = {
  hr_index?: number;
  hit_index?: number;
  k_index?: number;
  bb_index?: number;
  double_index?: number;
  sample_pa_coors?: number;
  sample_pa_league?: number;
};

export default function CoorsLabPage() {
  const [season, setSeason] = useState(2024);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchCoorsSummary(season)
      .then(setData)
      .catch((e: Error) => {
        setData(null);
        setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [season]);

  const pc = (data?.park_comparison as { coors_field?: RateRow; league_average?: RateRow }) ?? {};
  const factors = (data?.factors as Factors) ?? {};
  const trend = (data?.coors_trend_by_season as RateRow[]) ?? [];
  const stadiums = (data?.top_hr_stadiums as RateRow[]) ?? [];
  const rockies = (data?.rockies_offense as { splits?: Array<RateRow & { split?: string }> })?.splits ?? [];

  const fmtIndex = (v: number | undefined) => (v != null ? v.toFixed(3) : "—");
  const indexHint = (v: number | undefined) =>
    v == null ? undefined : v > 1.02 ? "Above league" : v < 0.98 ? "Below league" : "Near league";

  const compareData = [
    { name: "Home run", Coors: Number(pc.coors_field?.hr_rate ?? 0), League: Number(pc.league_average?.hr_rate ?? 0) },
    { name: "Hit", Coors: Number(pc.coors_field?.hit_rate ?? 0), League: Number(pc.league_average?.hit_rate ?? 0) },
    { name: "Strikeout", Coors: Number(pc.coors_field?.k_rate ?? 0), League: Number(pc.league_average?.k_rate ?? 0) },
  ];

  const rockiesChart = rockies.map((r) => ({
    split: r.split === "at_coors" ? "At Coors" : "Away",
    hr_rate: Number(r.hr_rate),
    hit_rate: Number(r.hit_rate),
  }));

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white">Coors Field Lab</h2>
          <p className="mt-1 text-sm text-slate-400 max-w-2xl">
            Descriptive park effects from plate-appearance outcomes. Index{" "}
            <strong className="text-slate-300">1.000</strong> = same rate as league that season; above 1 means more
            frequent at Coors (not a causal altitude estimate).
          </p>
        </div>
        <label className="text-sm text-slate-400">
          Season{" "}
          <select
            className="ml-2 rounded border border-navy-700 bg-navy-800 px-2 py-1 text-white"
            value={season}
            onChange={(e) => setSeason(Number(e.target.value))}
          >
            {[2021, 2022, 2023, 2024, 2025].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      </header>

      {loading ? <p className="text-slate-400">Loading…</p> : null}
      {error ? (
        <p className="text-sm text-red-300">Could not load Coors data: {error}. Is the API running?</p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Home run index"
          value={fmtIndex(factors.hr_index)}
          hint={indexHint(factors.hr_index)}
        />
        <StatCard label="Hit index" value={fmtIndex(factors.hit_index)} hint={indexHint(factors.hit_index)} />
        <StatCard
          label="Strikeout index"
          value={fmtIndex(factors.k_index)}
          hint={indexHint(factors.k_index)}
        />
        <StatCard label="Walk index" value={fmtIndex(factors.bb_index)} hint={indexHint(factors.bb_index)} />
        <StatCard label="Double index" value={fmtIndex(factors.double_index)} hint={indexHint(factors.double_index)} />
      </div>

      {factors.sample_pa_coors ? (
        <p className="text-xs text-slate-500">
          Sample: {factors.sample_pa_coors?.toLocaleString()} PAs at Coors vs{" "}
          {factors.sample_pa_league?.toLocaleString()} league PAs in {season}.
        </p>
      ) : null}

      <div className="rounded-lg border border-navy-700 bg-navy-900/50 p-4 h-80">
        <p className="text-sm font-medium text-slate-300 mb-2">Coors Field vs league (per plate appearance)</p>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={compareData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #334155" }} />
            <Legend />
            <Bar dataKey="Coors" fill="#7c6cf0" />
            <Bar dataKey="League" fill="#475569" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {rockiesChart.length > 0 ? (
        <div className="rounded-lg border border-navy-700 bg-navy-900/50 p-4 h-72">
          <p className="text-sm font-medium text-slate-300 mb-2">Rockies offense: home (Coors) vs away</p>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={rockiesChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="split" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #334155" }} />
              <Legend />
              <Bar dataKey="hr_rate" name="HR rate" fill="#c084fc" />
              <Bar dataKey="hit_rate" name="Hit rate" fill="#64748b" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}

      <div className="rounded-lg border border-navy-700 bg-navy-900/50 p-4 h-80">
        <p className="text-sm font-medium text-slate-300 mb-2">Home-run rate at Coors by season</p>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={trend.map((t) => ({ season: t.season, hr_rate: Number(t.hr_rate) }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="season" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #334155" }} />
            <Line type="monotone" dataKey="hr_rate" stroke="#7c6cf0" strokeWidth={2} dot />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto rounded-lg border border-navy-700">
        <table className="w-full text-sm">
          <thead className="bg-navy-800 text-left text-slate-400">
            <tr>
              <th className="p-3">Stadium</th>
              <th className="p-3">Home runs per PA</th>
              <th className="p-3">Sample PA</th>
            </tr>
          </thead>
          <tbody>
            {stadiums.map((s) => (
              <tr key={String(s.stadium_id)} className="border-t border-navy-700">
                <td className="p-3 text-white">
                  {String(s.name)}
                  {s.is_coors_field ? (
                    <span className="ml-2 text-xs text-accent-purple">Coors</span>
                  ) : null}
                </td>
                <td className="p-3 tabular-nums">{Number(s.hr_rate).toFixed(4)}</td>
                <td className="p-3 tabular-nums">{Number(s.pa).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
