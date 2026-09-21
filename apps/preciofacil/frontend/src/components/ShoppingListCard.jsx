import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useUser } from "../store.jsx";
import SupermarketBadge from "./SupermarketBadge.jsx";
import SupermarketLogo from "./SupermarketLogo.jsx";

export default function ShoppingListCard() {
  const { userEmail } = useUser();
  const [categories, setCategories] = useState([]);
  const [plan, setPlan] = useState(null);
  const [adding, setAdding] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [showChart, setShowChart] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [dismissed, setDismissed] = useState(new Set());

  const load = () => {
    api.shoppingList(userEmail).then(setPlan).catch(() => {});
  };

  const loadSuggestions = () => {
    api.reorderSuggestions(userEmail).then(setSuggestions).catch(() => {});
  };

  useEffect(() => {
    api.categories().then(setCategories).catch(() => {});
    load();
    loadSuggestions();
    setDismissed(new Set());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail]);

  const addedSlugs = new Set((plan?.items ?? []).map((i) => i.category_slug));
  const available = categories.filter((c) => !addedSlugs.has(c.slug));

  const handleAdd = async (slug) => {
    setAdding(true);
    setPickerOpen(false);
    try {
      const updated = await api.addShoppingListItem(userEmail, slug);
      setPlan(updated);
      setSuggestions((prev) => prev.filter((s) => s.category_slug !== slug));
    } finally {
      setAdding(false);
    }
  };

  const dismissSuggestion = (slug) => {
    setDismissed((prev) => new Set(prev).add(slug));
  };

  const handleRemove = async (id) => {
    const updated = await api.removeShoppingListItem(id, userEmail);
    setPlan(updated);
  };

  if (!plan) return null;

  return (
    <div className="mb-5 rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
          🛒 Tu lista de la compra
        </h2>
        {plan.items.length > 0 && (
          <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
            {plan.total_optimal.toFixed(2)}€
          </span>
        )}
      </div>

      {plan.items.length === 0 && (
        <p className="mb-3 text-xs text-slate-400">
          Añade los tipos de producto que sueles comprar y te decimos dónde te sale más a
          cuenta cada uno.
        </p>
      )}

      <div className="space-y-1.5">
        {plan.items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between gap-2 rounded-xl px-1.5 py-1 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/60"
          >
            <div className="flex min-w-0 items-center gap-2">
              <span className="text-base">{item.category_icon}</span>
              <span className="truncate text-sm text-slate-700 dark:text-slate-200">
                {item.category_label}
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {item.best_supermarket_slug ? (
                <>
                  <SupermarketBadge
                    slug={item.best_supermarket_slug}
                    name={item.best_supermarket_name}
                    color={item.best_supermarket_color}
                    emoji={item.best_supermarket_emoji}
                  />
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {item.best_price.toFixed(2)}€
                  </span>
                </>
              ) : (
                <span className="text-xs text-slate-400">Sin precio aún</span>
              )}
              <button
                onClick={() => handleRemove(item.id)}
                className="press text-slate-300 transition-colors hover:text-red-500"
                aria-label="Quitar"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>

      {suggestions.filter((s) => !dismissed.has(s.category_slug)).length > 0 && (
        <div className="mt-3 space-y-1.5">
          {suggestions
            .filter((s) => !dismissed.has(s.category_slug))
            .map((s) => (
              <div
                key={s.category_slug}
                className="flex items-center justify-between gap-2 rounded-xl border border-dashed border-brand-300/70 bg-brand-50/60 px-2.5 py-1.5 dark:border-brand-700/60 dark:bg-brand-950/40"
              >
                <div className="flex min-w-0 items-center gap-1.5">
                  <span className="text-base">{s.category_icon}</span>
                  <span className="min-w-0 truncate text-xs text-brand-800 dark:text-brand-200">
                    🔁 Sueles comprar <strong>{s.category_label.toLowerCase()}</strong> cada{" "}
                    {s.avg_interval_days} días · hace {s.days_since_last}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    onClick={() => handleAdd(s.category_slug)}
                    className="press rounded-lg bg-brand-600 px-2 py-1 text-[11px] font-bold text-white shadow-sm"
                  >
                    + Añadir
                  </button>
                  <button
                    onClick={() => dismissSuggestion(s.category_slug)}
                    className="press text-slate-300 transition-colors hover:text-red-500"
                    aria-label="Descartar sugerencia"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
        </div>
      )}

      {available.length > 0 && (
        <div className="relative mt-3">
          <button
            onClick={() => setPickerOpen((v) => !v)}
            disabled={adding}
            className="press w-full rounded-xl border border-dashed border-slate-300 py-2 text-xs font-semibold text-slate-500 transition-colors hover:border-brand-500 hover:text-brand-600 disabled:opacity-50 dark:border-slate-700 dark:text-slate-400"
          >
            {adding ? "Añadiendo…" : "+ Añadir producto"}
          </button>
          {pickerOpen && (
            <div className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white/95 p-1 shadow-xl backdrop-blur-sm dark:border-slate-700 dark:bg-slate-800/95">
              {available.map((c) => (
                <button
                  key={c.slug}
                  onClick={() => handleAdd(c.slug)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  <span>{c.icon}</span>
                  {c.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {plan.items.length > 1 && plan.totals_by_supermarket?.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setShowChart((v) => !v)}
            className="press w-full rounded-xl border border-slate-200 py-2 text-xs font-semibold text-slate-500 transition-colors hover:border-brand-400 hover:text-brand-600 dark:border-slate-700 dark:text-slate-400"
          >
            {showChart ? "Ocultar comparativa" : "📊 Comparar cesta por supermercado"}
          </button>
          {showChart && (
            <div className="mt-3">
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={plan.totals_by_supermarket} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
                    <XAxis dataKey="supermarket_name" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                    <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" tickFormatter={(v) => `${v}€`} />
                    <Tooltip
                      formatter={(value, _name, props) => [
                        `${value.toFixed(2)}€ (${props.payload.items_covered}/${props.payload.items_total} productos)`,
                        props.payload.supermarket_name,
                      ]}
                    />
                    <Bar dataKey="total" radius={[6, 6, 0, 0]}>
                      {plan.totals_by_supermarket.map((entry) => (
                        <Cell key={entry.supermarket_slug} fill={entry.supermarket_color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-1 flex flex-wrap gap-2">
                {plan.totals_by_supermarket.map((t) => (
                  <div key={t.supermarket_slug} className="flex items-center gap-1 text-[10px] text-slate-400">
                    <SupermarketLogo slug={t.supermarket_slug} color={t.supermarket_color} emoji={t.supermarket_emoji} className="h-4 w-4" />
                    {t.items_covered < t.items_total && <span>({t.items_covered}/{t.items_total})</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {plan.savings_amount ? (
        <p className="mt-3 rounded-xl bg-brand-50 p-2.5 text-xs text-brand-800 dark:bg-brand-950 dark:text-brand-200">
          💡 Repartiendo la compra ahorras <strong>{plan.savings_amount.toFixed(2)}€</strong> (
          {Math.round(plan.savings_pct)}%) frente a comprarlo todo en{" "}
          {plan.single_stop_supermarket_name}, que costaría {plan.single_stop_total.toFixed(2)}€.
        </p>
      ) : plan.items.length > 1 && plan.single_stop_supermarket_name ? (
        <p className="mt-3 text-xs text-slate-400">
          {plan.single_stop_supermarket_name} ya te sale igual de bien comprándolo todo junto.
        </p>
      ) : null}
    </div>
  );
}
