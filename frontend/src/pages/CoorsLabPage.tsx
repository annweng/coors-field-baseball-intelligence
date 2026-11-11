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

export default function CoorsLabPage() {
  const [season, setSeason] = useState(2024);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCoorsSummary(season)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [season]);

  const pc = (data?.park_comparison as { coors_field?: RateRow; league_average?: RateRow }) ?? {};
  const factors = (data?.factors as Record<string, number>) ?? {};
  const trend = (data?.coors_trend_by_season as RateRow[]) ?? [];
  const stadiums = (data?.top_hr_stadiums as RateRow[]) ?? [];

  const compareData = [
    { name: "HR rate", Coors: Number(pc.coors_field?.hr_rate ?? 0), League: Number(pc.league_average?.hr_rate ?? 0) },
    { name: "Hit rate", Coors: Number(pc.coors_field?.hit_rate ?? 0), League: Number(pc.league_average?.hit_rate ?? 0) },
    { name: "K rate", Coors: Number(pc.coors_field?.k_rate ?? 0), League: Number(pc.league_average?.k_rate ?? 0) },
  ];

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white">Coors Field Lab</h2>
          <p className="mt-1 text-sm text-slate-400 max-w-2xl">
            Descriptive park effects from plate-appearance outcomes. Differences reflect many factors
            (talent, weather, altitude); they are not automatic causal claims.
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

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="HR index (Coors / league)" value={factors.hr_index?.toFixed(3) ?? "—"} />
        <StatCard label="Hit index" value={factors.hit_index?.toFixed(3) ?? "—"} />
        <StatCard label="K index" value={factors.k_index?.toFixed(3) ?? "—"} />
      </div>

      <div className="rounded-lg border border-navy-700 bg-navy-900/50 p-4 h-80">
        <p className="text-sm font-medium text-slate-300 mb-2">Coors Field vs league (per PA)</p>
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
              <th className="p-3">HR / PA</th>
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
