type Props = { label: string; value: string; hint?: string };

export function StatCard({ label, value, hint }: Props) {
  return (
    <div className="rounded-lg border border-navy-700 bg-navy-900/80 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white tabular-nums">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
