import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";
import SupermarketBadge from "./SupermarketBadge.jsx";

export default function ShoppingListCard() {
  const { userEmail } = useUser();
  const [categories, setCategories] = useState([]);
  const [plan, setPlan] = useState(null);
  const [adding, setAdding] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

  const load = () => {
    api.shoppingList(userEmail).then(setPlan).catch(() => {});
  };

  useEffect(() => {
    api.categories().then(setCategories).catch(() => {});
    load();
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
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (id) => {
    const updated = await api.removeShoppingListItem(id, userEmail);
    setPlan(updated);
  };

  if (!plan) return null;

  return (
    <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
          🛒 Tu lista de la compra
        </h2>
        {plan.items.length > 0 && (
          <span className="text-lg font-extrabold text-slate-900 dark:text-white">
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

      <div className="space-y-2">
        {plan.items.map((item) => (
          <div key={item.id} className="flex items-center justify-between gap-2">
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
                className="text-slate-300 hover:text-red-500"
                aria-label="Quitar"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>

      {available.length > 0 && (
        <div className="relative mt-3">
          <button
            onClick={() => setPickerOpen((v) => !v)}
            disabled={adding}
            className="w-full rounded-xl border border-dashed border-slate-300 py-2 text-xs font-semibold text-slate-500 hover:border-brand-500 hover:text-brand-600 disabled:opacity-50 dark:border-slate-700 dark:text-slate-400"
          >
            {adding ? "Añadiendo…" : "+ Añadir producto"}
          </button>
          {pickerOpen && (
            <div className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-800">
              {available.map((c) => (
                <button
                  key={c.slug}
                  onClick={() => handleAdd(c.slug)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  <span>{c.icon}</span>
                  {c.label}
                </button>
              ))}
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
