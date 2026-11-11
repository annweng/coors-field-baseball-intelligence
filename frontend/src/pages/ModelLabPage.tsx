import { useEffect, useState } from "react";
import {
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
import { fetchActiveModels, fetchModelEvals } from "../lib/api";

function CalibrationChart({
  title,
  points,
}: {
  title: string;
  points: Array<{ bin: number; mean_predicted: number; empirical_rate: number }>;
}) {
  const data = points.map((p) => ({
    bin: p.bin,
    predicted: p.mean_predicted,
    actual: p.empirical_rate,
  }));
  return (
    <div className="rounded-lg border border-navy-700 bg-navy-900/40 p-4">
      <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="bin" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} domain={[0, "auto"]} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Legend />
            <Line type="monotone" dataKey="predicted" name="Mean predicted" stroke="#a855f7" dot />
            <Line type="monotone" dataKey="actual" name="Empirical" stroke="#38bdf8" dot />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function ModelLabPage() {
  const [evals, setEvals] = useState<Awaited<ReturnType<typeof fetchModelEvals>> | null>(null);
  const [active, setActive] = useState<Awaited<ReturnType<typeof fetchActiveModels>> | null>(null);

  useEffect(() => {
    Promise.all([fetchModelEvals(), fetchActiveModels()])
      .then(([e, a]) => {
        setEvals(e);
        setActive(a);
      })
      .catch(() => {
        setEvals(null);
        setActive(null);
      });
  }, []);

  const pa = active?.plate_appearance;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-white">Model Lab</h2>
      <p className="text-sm text-slate-400 max-w-3xl">
        Production models and stored evaluation runs. Active PA model:{" "}
        <span className="text-white font-medium">{pa?.model_version ?? "—"}</span>
        {pa?.beats_baseline ? " (beats baseline on 2024 holdout)" : ""}.
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="PA test log loss"
          value={pa?.test_log_loss != null ? pa.test_log_loss.toFixed(3) : "—"}
          hint={
            pa?.baseline_log_loss != null
              ? `Baseline ${pa.baseline_log_loss.toFixed(3)}`
              : undefined
          }
        />
        <StatCard
          label="Holdout PAs"
          value={pa?.test_n != null ? pa.test_n.toLocaleString() : "—"}
        />
        <StatCard
          label="Runs test MAE"
          value={
            active?.runs?.test_mae != null ? active.runs.test_mae.toFixed(2) : "—"
          }
          hint={
            active?.runs?.baseline_mae != null
              ? `Baseline ${active.runs.baseline_mae.toFixed(2)}`
              : undefined
          }
        />
        <StatCard
          label="Runs model"
          value={active?.runs?.model_version ?? "—"}
          hint={active?.runs?.beats_baseline ? "beats baseline" : "baseline fallback"}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {pa?.calibration_k?.points?.length ? (
          <CalibrationChart title="Strikeout calibration (test)" points={pa.calibration_k.points} />
        ) : null}
        {pa?.calibration_hr?.points?.length ? (
          <CalibrationChart title="Home run calibration (test)" points={pa.calibration_hr.points} />
        ) : null}
      </div>

      <div className="overflow-x-auto rounded-lg border border-navy-700">
        <table className="w-full text-sm">
          <thead className="bg-navy-800 text-slate-400 text-left">
            <tr>
              <th className="p-3">Version</th>
              <th className="p-3">Type</th>
              <th className="p-3">Test log loss</th>
              <th className="p-3">vs baseline</th>
              <th className="p-3">Evaluated</th>
            </tr>
          </thead>
          <tbody>
            {(evals?.evaluations ?? []).map((e) => (
              <tr key={e.model_version + e.created_at} className="border-t border-navy-700">
                <td className="p-3 text-white font-medium">{e.model_version}</td>
                <td className="p-3 text-slate-300">{e.evaluation_type}</td>
                <td className="p-3 tabular-nums">
                  {e.test_log_loss != null ? e.test_log_loss.toFixed(4) : "—"}
                </td>
                <td className="p-3">
                  {e.beats_baseline == null
                    ? "—"
                    : e.beats_baseline
                      ? "Beats"
                      : "Below"}
                </td>
                <td className="p-3 text-slate-500">{e.created_at ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="rounded-lg border border-navy-700 bg-navy-900/40 p-4 text-sm text-slate-300 space-y-2">
        <h3 className="font-semibold text-white">Architecture</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li>Baseline PA: smoothed batter/pitcher/league rate blend (`baseline-v0.1.0`)</li>
          <li>Production PA: XGBoost stacked on baseline probs (`xgb-v0.2.2`)</li>
          <li>Runs: ridge on 30-day team offense/defense + Coors flag (`runs-v0.1.0`)</li>
          <li>Chronological splits; unknown PA outcomes excluded</li>
        </ul>
      </section>
    </div>
  );
}
