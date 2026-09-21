import { useEffect, useState } from "react";
import { api } from "../api.js";
import SupermarketBadge from "../components/SupermarketBadge.jsx";
import PriceTag from "../components/PriceTag.jsx";
import ProductThumb from "../components/ProductThumb.jsx";
import ProductDetailSheet from "../components/ProductDetailSheet.jsx";

export default function CompareScreen() {
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);

  useEffect(() => {
    api.categories().then(setCategories).catch((err) => setError(err.message));
  }, []);

  const selectCategory = (slug) => {
    setSelectedCategory(slug);
    setLoading(true);
    setError(null);
    api
      .compareCategory(slug)
      .then(setComparison)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  return (
    <div className="px-4 pt-4">
      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        Elige un tipo de producto y compáralo entre supermercados.
      </p>

      <div className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {categories.map((c) => (
          <button
            key={c.slug}
            onClick={() => selectCategory(c.slug)}
            className={`press flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-2 text-xs font-semibold transition-all ${
              selectedCategory === c.slug
                ? "border-transparent bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md shadow-brand-700/25"
                : "border-slate-200/70 bg-white text-slate-600 shadow-sm dark:border-slate-700/70 dark:bg-slate-900 dark:text-slate-300"
            }`}
          >
            <span>{c.icon}</span>
            {c.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {!selectedCategory && (
        <div className="mt-10 text-center text-sm text-slate-400">
          Prueba con "pasta", "leche", "fuet y embutido" o "detergente de lavadora" 👆
        </div>
      )}

      {loading && (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
      )}

      {!loading && comparison && (
        <div className="space-y-2">
          {comparison.products.length === 0 && (
            <p className="mt-6 text-center text-sm text-slate-400">
              Aún no tenemos precios de esta categoría. Prueba a actualizar desde la pestaña "Hoy".
            </p>
          )}
          {comparison.products.map((p, idx) => (
            <button
              key={p.product_id}
              onClick={() => setSelectedProduct(p)}
              className={`press flex w-full gap-3 rounded-2xl border p-3 text-left transition-shadow hover:shadow-md ${
                idx === 0
                  ? "border-brand-300/70 bg-gradient-to-br from-brand-50 to-white shadow-sm dark:border-brand-700/50 dark:from-brand-950 dark:to-slate-900"
                  : "border-slate-200/70 bg-white shadow-sm dark:border-slate-800/70 dark:bg-slate-900"
              }`}
            >
              <ProductThumb src={p.image_url} alt={p.name} emoji={comparison.category.icon} className="h-12 w-12" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <SupermarketBadge slug={p.supermarket_slug} name={p.supermarket_name} color={p.supermarket_color} emoji={p.supermarket_emoji} />
                  {idx === 0 && (
                    <span className="rounded-full bg-gradient-to-br from-brand-500 to-brand-700 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                      MÁS BARATO
                    </span>
                  )}
                </div>
                <p className="mt-1 truncate text-xs text-slate-600 dark:text-slate-300">{p.name}</p>
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
            </button>
          ))}
        </div>
      )}

      {selectedProduct && (
        <ProductDetailSheet
          product={selectedProduct}
          categoryIcon={comparison?.category?.icon}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </div>
  );
}
