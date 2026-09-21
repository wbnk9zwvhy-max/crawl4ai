import { useEffect, useState } from "react";
import { api } from "../api.js";
import SupermarketBadge from "../components/SupermarketBadge.jsx";
import SupermarketLogo from "../components/SupermarketLogo.jsx";
import PriceTag from "../components/PriceTag.jsx";
import ProductThumb from "../components/ProductThumb.jsx";
import SavingsTeaser from "../components/SavingsTeaser.jsx";
import ShoppingListCard from "../components/ShoppingListCard.jsx";
import ProductDetailSheet from "../components/ProductDetailSheet.jsx";

const PERIODS = [
  { id: "today", label: "Hoy" },
  { id: "week", label: "Esta semana" },
];

export default function OffersScreen({ onNavigate }) {
  const [period, setPeriod] = useState("today");
  const [supermarkets, setSupermarkets] = useState([]);
  const [activeSupermarket, setActiveSupermarket] = useState(null);
  const [groups, setGroups] = useState(null);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.supermarkets().then(setSupermarkets).catch(() => {});
  }, []);

  const load = () => {
    setError(null);
    api
      .offersToday({ period, supermarket: activeSupermarket })
      .then(setGroups)
      .catch((err) => setError(err.message));
  };

  useEffect(load, [period, activeSupermarket]);

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

  const toggleSupermarket = (slug) => {
    setActiveSupermarket((current) => (current === slug ? null : slug));
  };

  return (
    <div className="px-4 pt-4">
      <SavingsTeaser onNavigate={onNavigate} />

      {/* Selector Hoy / Esta semana */}
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex rounded-full bg-slate-100/80 p-1 ring-1 ring-slate-200/70 dark:bg-slate-800/80 dark:ring-slate-700/70">
          {PERIODS.map((p) => (
            <button
              key={p.id}
              onClick={() => setPeriod(p.id)}
              className={`press rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
                period === p.id
                  ? "bg-white text-brand-700 shadow-sm dark:bg-slate-700 dark:text-brand-300"
                  : "text-slate-500 dark:text-slate-400"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="press shrink-0 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 px-3 py-1.5 text-xs font-semibold text-white shadow-md shadow-brand-700/25 disabled:opacity-50"
        >
          {refreshing ? "Actualizando…" : "↻ Actualizar"}
        </button>
      </div>

      {/* Accesos rápidos a supermercados */}
      <div className="-mx-4 mb-4 flex gap-3 overflow-x-auto px-4 pb-1">
        <button
          onClick={() => setActiveSupermarket(null)}
          className={`press flex shrink-0 flex-col items-center gap-1 rounded-2xl border px-3 py-2 text-[11px] font-semibold transition-all ${
            activeSupermarket === null
              ? "border-transparent bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md shadow-brand-700/25"
              : "border-slate-200/70 bg-white text-slate-600 shadow-sm dark:border-slate-700/70 dark:bg-slate-900 dark:text-slate-300"
          }`}
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20 text-lg">
            🛒
          </span>
          Todos
        </button>
        {supermarkets
          .filter((s) => s.slug !== "kuups")
          .map((s) => (
            <button
              key={s.slug}
              onClick={() => toggleSupermarket(s.slug)}
              className={`press flex shrink-0 flex-col items-center gap-1 rounded-2xl border px-3 py-2 text-[11px] font-semibold transition-all ${
                activeSupermarket === s.slug
                  ? "border-transparent bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md shadow-brand-700/25"
                  : "border-slate-200/70 bg-white text-slate-600 shadow-sm dark:border-slate-700/70 dark:bg-slate-900 dark:text-slate-300"
              }`}
            >
              <SupermarketLogo slug={s.slug} color={s.color} emoji={s.logo_emoji} className="h-9 w-9" />
              {s.name}
            </button>
          ))}
      </div>

      <ShoppingListCard />

      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        {period === "today"
          ? "Ofertas destacadas de hoy, agrupadas por producto."
          : "Los mejores precios vistos esta semana, agrupados por producto."}
        {activeSupermarket &&
          ` Filtrado por ${supermarkets.find((s) => s.slug === activeSupermarket)?.name ?? ""}.`}
      </p>

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
          Todavía no hay ofertas detectadas{activeSupermarket ? " para este supermercado" : ""}.
          Pulsa "Actualizar" o espera al análisis automático de las 8:00.
        </div>
      )}

      <div className="space-y-5">
        {groups?.map((group) => (
          <section key={group.category.slug}>
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-lg shadow-sm ring-1 ring-slate-100 dark:bg-slate-800 dark:ring-slate-700">
                {group.category.icon}
              </span>
              <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                {group.category.label}
              </h2>
            </div>
            <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1">
              {group.products.map((p) => (
                <button
                  key={p.product_id}
                  onClick={() => setSelected({ product: p, categoryIcon: group.category.icon })}
                  className="press w-44 shrink-0 rounded-2xl border border-slate-200/70 bg-white p-3 text-left shadow-sm transition-shadow hover:shadow-md dark:border-slate-800/70 dark:bg-slate-900"
                >
                  <ProductThumb
                    src={p.image_url}
                    alt={p.name}
                    emoji={group.category.icon}
                    className="mb-2 h-20 w-full"
                  />
                  <SupermarketBadge slug={p.supermarket_slug} name={p.supermarket_name} color={p.supermarket_color} emoji={p.supermarket_emoji} />
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
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      {selected && (
        <ProductDetailSheet
          product={selected.product}
          categoryIcon={selected.categoryIcon}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
