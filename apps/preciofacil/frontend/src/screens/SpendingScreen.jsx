import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useUser } from "../store.jsx";
import SupermarketLogo from "../components/SupermarketLogo.jsx";

function MonthDelta({ current, previous }) {
  if (previous === null || previous === undefined || previous === 0) return null;
  const delta = current - previous;
  const pct = Math.round((delta / previous) * 100);
  if (Math.abs(pct) < 1) {
    return <span className="text-xs text-slate-400">Igual que el mes anterior</span>;
  }
  const up = delta > 0;
  return (
    <span className={`text-xs font-semibold ${up ? "text-red-500" : "text-emerald-500"}`}>
      {up ? "▲" : "▼"} {Math.abs(pct)}% vs. mes anterior
    </span>
  );
}

export default function SpendingScreen() {
  const { userEmail } = useUser();
  const [spending, setSpending] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .spending(userEmail)
      .then(setSpending)
      .catch((err) => setError(err.message));
  }, [userEmail]);

  if (error) {
    return (
      <div className="px-4 pt-4">
        <p className="text-sm text-red-500">{error}</p>
      </div>
    );
  }

  if (!spending) return null;

  const maxCategory = spending.by_category[0]?.total ?? 0;
  const maxSupermarket = spending.by_supermarket[0]?.total ?? 0;

  return (
    <div className="px-4 pt-4">
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Cuánto gastas mes a mes en la compra, según lo que has registrado en "Mis compras".
      </p>

      {spending.monthly.length === 0 && (
        <div className="mt-10 text-center text-sm text-slate-400">
          Registra alguna compra en "Mis compras" (a mano o subiendo un ticket) y aquí verás tu
          gasto mes a mes. 📊
        </div>
      )}

      {spending.monthly.length > 0 && (
        <>
          <div className="relative mb-5 overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-600 to-brand-800 p-4 text-white shadow-lg shadow-brand-700/25">
            <div
              className="pointer-events-none absolute -right-8 -top-12 h-36 w-36 rounded-full bg-white/10 blur-2xl"
              aria-hidden="true"
            />
            <p className="relative text-xs font-semibold uppercase tracking-wider text-brand-100">
              Gasto de este mes
            </p>
            <p className="relative text-3xl font-extrabold tracking-tight">
              {spending.current_month_total.toFixed(2)}€
            </p>
            <div className="relative mt-1 flex items-center gap-2 text-xs text-brand-100">
              <span>Media mensual: {spending.avg_monthly.toFixed(2)}€</span>
              <MonthDelta current={spending.current_month_total} previous={spending.previous_month_total} />
            </div>
          </div>

          <div className="mb-5 rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
              Gasto por mes
            </h2>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={spending.monthly} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                  <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" tickFormatter={(v) => `${v}€`} />
                  <Tooltip formatter={(value) => [`${value.toFixed(2)}€`, "Gasto"]} />
                  <Bar dataKey="total" radius={[6, 6, 0, 0]} fill="#0d9488" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mb-5 rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
              Por tipo de producto
            </h2>
            <div className="space-y-2">
              {spending.by_category.map((c) => (
                <div key={c.category_slug} className="flex items-center gap-2">
                  <span className="w-5 shrink-0 text-center text-sm">{c.category_icon}</span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-0.5 flex items-center justify-between gap-2">
                      <span className="truncate text-xs text-slate-600 dark:text-slate-300">
                        {c.category_label}
                      </span>
                      <span className="shrink-0 text-xs font-semibold text-slate-800 dark:text-slate-100">
                        {c.total.toFixed(2)}€
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                        style={{ width: `${maxCategory ? (c.total / maxCategory) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
              Por supermercado
            </h2>
            <div className="space-y-2">
              {spending.by_supermarket.map((s) => (
                <div key={s.supermarket_slug} className="flex items-center gap-2">
                  <SupermarketLogo slug={s.supermarket_slug} color={s.supermarket_color} emoji={s.supermarket_emoji} className="h-6 w-6 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="mb-0.5 flex items-center justify-between gap-2">
                      <span className="truncate text-xs text-slate-600 dark:text-slate-300">
                        {s.supermarket_name}
                      </span>
                      <span className="shrink-0 text-xs font-semibold text-slate-800 dark:text-slate-100">
                        {s.total.toFixed(2)}€
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${maxSupermarket ? (s.total / maxSupermarket) * 100 : 0}%`,
                          backgroundColor: s.supermarket_color,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
