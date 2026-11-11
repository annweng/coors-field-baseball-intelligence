export default function DataPage() {
  return (
    <div className="space-y-6 max-w-3xl text-sm text-slate-300 leading-relaxed">
      <h2 className="text-2xl font-semibold text-white">Data &amp; Engineering</h2>

      <section className="space-y-2">
        <h3 className="text-white font-medium">Stack</h3>
        <p>Statcast via pybaseball → parquet cache → PostgreSQL → FastAPI → React (Vite + Tailwind).</p>
      </section>

      <section className="space-y-2">
        <h3 className="text-white font-medium">Local run</h3>
        <pre className="rounded bg-navy-900 border border-navy-700 p-4 text-xs overflow-x-auto text-slate-200">
          {`docker compose up postgres -d
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev`}
        </pre>
        <p>Postgres on <strong>localhost:5433</strong> if 5432 is taken. API docs: /docs</p>
      </section>

      <section className="space-y-2">
        <h3 className="text-white font-medium">Documentation</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li><code>docs/architecture.md</code></li>
          <li><code>docs/etl.md</code></li>
          <li><code>docs/dataset-2021-2025.md</code></li>
          <li><code>docs/features.md</code></li>
          <li><code>docs/ROADMAP.md</code> — deferred XGBoost retrain</li>
        </ul>
      </section>
    </div>
  );
}
