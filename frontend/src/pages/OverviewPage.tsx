import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StatCard } from "../components/StatCard";
import { fetchActiveModels, fetchStatus } from "../lib/api";

export default function OverviewPage() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof fetchStatus>> | null>(null);
  const [active, setActive] = useState<Awaited<ReturnType<typeof fetchActiveModels>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchStatus(), fetchActiveModels()])
      .then(([s, a]) => {
        setStatus(s);
        setActive(a);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const paActive = active?.plate_appearance;

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="text-3xl font-semibold text-white">Baseball analytics at altitude</h2>
        <p className="max-w-3xl text-slate-300 leading-relaxed">
          Statcast-derived plate appearances (2021–2025), Coors Field research, multiclass PA
          forecasts, and team run expectations. Independent fan/research project — not affiliated
          with MLB or the Rockies.
        </p>
      </section>

      {error ? (
        <div className="rounded-lg border border-amber-900/50 bg-amber-950/30 p-4 text-amber-200 text-sm">
          API unavailable: {error}. Start the backend on port 8000 and Postgres on 5433.
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Plate appearances" value={status ? status.plate_appearances.toLocaleString() : "—"} />
        <StatCard label="MLB teams" value={status ? String(status.teams) : "—"} />
        <StatCard
          label="Active PA model"
          value={paActive?.model_version ?? "—"}
          hint={paActive?.beats_baseline ? "production XGB" : "baseline"}
        />
        <StatCard
          label="PA holdout log loss"
          value={paActive?.test_log_loss != null ? paActive.test_log_loss.toFixed(3) : "—"}
        />
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          { to: "/coors", title: "Coors Field Lab", desc: "Park vs league rates, Rockies splits, stadium leaderboards." },
          { to: "/models", title: "Model Lab", desc: "Holdout metrics, calibration charts, evaluation history." },
          { to: "/forecasts", title: "Player Forecasts", desc: "Multiclass PA probabilities for batter–pitcher matchups." },
        ].map((m) => (
          <Link
            key={m.to}
            to={m.to}
            className="rounded-lg border border-navy-700 bg-navy-800/40 p-5 hover:border-accent-purple/50 transition-colors"
          >
            <h3 className="font-semibold text-white">{m.title}</h3>
            <p className="mt-2 text-sm text-slate-400">{m.desc}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
