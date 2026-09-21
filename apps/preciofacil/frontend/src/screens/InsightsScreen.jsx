import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";
import SupermarketBadge from "../components/SupermarketBadge.jsx";

export default function InsightsScreen() {
  const { userEmail } = useUser();
  const [insights, setInsights] = useState(null);
  const [error, setError] = useState(null);
  const [alertsState, setAlertsState] = useState(null);

  useEffect(() => {
    api
      .insights(userEmail)
      .then(setInsights)
      .catch((err) => setError(err.message));
    api
      .priceAlerts(userEmail)
      .then(setAlertsState)
      .catch(() => {});
  }, [userEmail]);

  const unwatch = (productId) => {
    api
      .unwatchProduct(userEmail, productId)
      .then(setAlertsState)
      .catch(() => {});
  };

  const totalSavings = insights?.reduce((acc, i) => acc + i.savings_amount, 0) ?? 0;
  const triggered = alertsState?.triggered ?? [];

  return (
    <div className="px-4 pt-4">
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Basado en tu historial de compras, esto es lo que podrías ahorrar cambiando de supermercado.
      </p>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {triggered.length > 0 && (
        <div className="mb-5">
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
            🔔 Alertas de precio
          </h2>
          <div className="space-y-2">
            {triggered.map((a) => (
              <div
                key={a.watch_id}
                className="flex items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-3 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    <SupermarketBadge
                      slug={a.supermarket_slug}
                      name={a.supermarket_name}
                      color={a.supermarket_color}
                      emoji={a.supermarket_emoji}
                    />
                    {a.is_historic_low && (
                      <span className="rounded-full bg-amber-400 px-2 py-0.5 text-[10px] font-bold text-white">
                        Mínimo histórico
                      </span>
                    )}
                  </div>
                  <p className="truncate text-sm text-slate-700 dark:text-slate-200">{a.product_name}</p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Antes {a.watched_price.toFixed(2)}€ → ahora{" "}
                    <span className="font-bold text-amber-600 dark:text-amber-400">
                      {a.current_price.toFixed(2)}€
                    </span>{" "}
                    (ahorras {a.savings_amount.toFixed(2)}€)
                  </p>
                </div>
                <button
                  onClick={() => unwatch(a.product_id)}
                  className="press shrink-0 text-slate-300 transition-colors hover:text-red-500"
                  aria-label="Dejar de seguir"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {insights && insights.length > 0 && (
        <div className="relative mb-5 overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-600 to-brand-800 p-4 text-white shadow-lg shadow-brand-700/25">
          <div
            className="pointer-events-none absolute -right-8 -top-12 h-36 w-36 rounded-full bg-white/10 blur-2xl"
            aria-hidden="true"
          />
          <p className="relative text-xs font-semibold uppercase tracking-wider text-brand-100">
            Ahorro potencial detectado
          </p>
          <p className="relative text-3xl font-extrabold tracking-tight">{totalSavings.toFixed(2)}€</p>
          <p className="relative mt-1 text-xs text-brand-100">
            en {insights.length} tipo{insights.length === 1 ? "" : "s"} de producto que sueles comprar
          </p>
        </div>
      )}

      {insights && insights.length === 0 && (
        <div className="mt-10 text-center text-sm text-slate-400">
          Registra alguna compra en "Mis compras" y aquí te diremos si puedes
          ahorrar comprándola en otro supermercado. 💡
        </div>
      )}

      <div className="space-y-3">
        {insights?.map((i) => (
          <div
            key={i.id}
            className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800/70 dark:bg-slate-900"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm text-slate-700 dark:text-slate-200">{i.message}</p>
              <span className="shrink-0 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 px-2 py-1 text-xs font-bold text-white shadow-sm">
                +{i.savings_amount.toFixed(2)}€
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
