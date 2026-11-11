import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Overview" },
  { to: "/forecasts", label: "Player Forecasts" },
  { to: "/coors", label: "Coors Field Lab" },
  { to: "/runs", label: "Run Forecasting" },
  { to: "/models", label: "Model Lab" },
  { to: "/data", label: "Data & Engineering" },
];

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-navy-700 bg-navy-900/90 backdrop-blur sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-accent-purple font-semibold">
              Independent Research
            </p>
            <h1 className="text-lg font-semibold text-white">Coors Field Baseball Intelligence</h1>
          </div>
          <nav className="flex flex-wrap gap-1 text-sm">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md transition-colors ${
                    isActive
                      ? "bg-accent-violet/30 text-white"
                      : "text-slate-400 hover:text-white hover:bg-navy-800"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-navy-700 py-4 text-center text-xs text-slate-500">
        Not affiliated with MLB or the Colorado Rockies. Research use only.
      </footer>
    </div>
  );
}
