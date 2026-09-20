import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";

export default function InsightsScreen() {
  const { userEmail } = useUser();
  const [insights, setInsights] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .insights(userEmail)
      .then(setInsights)
      .catch((err) => setError(err.message));
  }, [userEmail]);

  const totalSavings = insights?.reduce((acc, i) => acc + i.savings_amount, 0) ?? 0;

  return (
    <div className="px-4 pt-4">
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Basado en tu historial de compras, esto es lo que podrías ahorrar cambiando de supermercado.
      </p>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {insights && insights.length > 0 && (
        <div className="mb-5 rounded-2xl bg-gradient-to-br from-brand-700 to-brand-500 p-4 text-white">
          <p className="text-xs font-medium uppercase tracking-wide text-brand-100">
            Ahorro potencial detectado
          </p>
          <p className="mt-1 text-3xl font-extrabold">{totalSavings.toFixed(2)}€</p>
          <p className="mt-1 text-xs text-brand-100">
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
            className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm text-slate-700 dark:text-slate-200">{i.message}</p>
              <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                +{i.savings_amount.toFixed(2)}€
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
