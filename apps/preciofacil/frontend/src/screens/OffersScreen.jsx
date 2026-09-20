import { useEffect, useState } from "react";
import { api } from "../api.js";
import SupermarketBadge from "../components/SupermarketBadge.jsx";
import PriceTag from "../components/PriceTag.jsx";
import ProductThumb from "../components/ProductThumb.jsx";

export default function OffersScreen() {
  const [groups, setGroups] = useState(null);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = () => {
    setError(null);
    api
      .offersToday()
      .then(setGroups)
      .catch((err) => setError(err.message));
  };

  useEffect(load, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.scrapeNow();
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="px-4 pt-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Ofertas destacadas de hoy, agrupadas por producto.
        </p>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="shrink-0 rounded-full bg-brand-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
        >
          {refreshing ? "Actualizando…" : "↻ Actualizar"}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950 dark:text-red-300">
          No se ha podido conectar con el backend: {error}
        </div>
      )}

      {!groups && !error && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
      )}

      {groups && groups.length === 0 && (
        <div className="mt-10 text-center text-sm text-slate-400">
          Todavía no hay ofertas detectadas. Pulsa "Actualizar" o espera al
          análisis automático de las 8:00.
        </div>
      )}

      <div className="space-y-5">
        {groups?.map((group) => (
          <section key={group.category.slug}>
            <div className="mb-2 flex items-center gap-2">
              <span className="text-xl">{group.category.icon}</span>
              <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                {group.category.label}
              </h2>
            </div>
            <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1">
              {group.products.map((p) => (
                <div
                  key={p.product_id}
                  className="w-44 shrink-0 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                >
                  <ProductThumb
                    src={p.image_url}
                    alt={p.name}
                    emoji={group.category.icon}
                    className="mb-2 h-20 w-full"
                  />
                  <SupermarketBadge name={p.supermarket_name} color={p.supermarket_color} emoji={p.supermarket_emoji} />
                  <p className="mt-2 line-clamp-2 text-xs font-medium text-slate-700 dark:text-slate-200">
                    {p.name}
                  </p>
                  <div className="mt-1">
                    <PriceTag
                      price={p.price}
                      previousPrice={p.previous_price}
                      discountPct={p.discount_pct}
                      unit={p.unit}
                      unitPrice={p.unit_price}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
