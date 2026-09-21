import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useUser } from "../store.jsx";
import ProductThumb from "./ProductThumb.jsx";
import SupermarketBadge from "./SupermarketBadge.jsx";
import PriceTag from "./PriceTag.jsx";

const dateFormatter = new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "short" });

export default function ProductDetailSheet({ product, categoryIcon, onClose }) {
  const { userEmail } = useUser();
  const [current, setCurrent] = useState(product);
  const [history, setHistory] = useState(null);
  const [similar, setSimilar] = useState(null);
  const [watchedIds, setWatchedIds] = useState([]);

  useEffect(() => setCurrent(product), [product]);

  useEffect(() => {
    setHistory(null);
    setSimilar(null);
    api
      .productHistory(current.product_id)
      .then((points) =>
        setHistory(points.map((p) => ({ ...p, label: dateFormatter.format(new Date(p.scraped_at)) })))
      )
      .catch(() => setHistory([]));
    api
      .similarProducts(current.product_id)
      .then(setSimilar)
      .catch(() => setSimilar([]));
    api
      .priceAlerts(userEmail)
      .then((state) => setWatchedIds(state.watched_product_ids))
      .catch(() => {});
  }, [current.product_id, userEmail]);

  const isWatching = watchedIds.includes(current.product_id);
  const toggleWatch = () => {
    const action = isWatching
      ? api.unwatchProduct(userEmail, current.product_id)
      : api.watchProduct(userEmail, current.product_id);
    action.then((state) => setWatchedIds(state.watched_product_ids)).catch(() => {});
  };

  const cheapestSimilarPrice = similar?.length ? Math.min(...similar.map((p) => p.price)) : null;
  const couldSave = cheapestSimilarPrice !== null && cheapestSimilarPrice < current.price;

  return (
    <div
      className="animate-fade-in fixed inset-0 z-30 flex items-end justify-center bg-slate-900/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="animate-sheet-in max-h-[85vh] w-full max-w-md overflow-y-auto rounded-t-[2rem] bg-white p-4 pb-8 shadow-2xl ring-1 ring-black/5 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-3 h-1.5 w-10 rounded-full bg-slate-200 dark:bg-slate-700" />

        <div className="flex gap-3">
          <ProductThumb src={current.image_url} alt={current.name} emoji={categoryIcon} className="h-20 w-20" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <SupermarketBadge
                slug={current.supermarket_slug}
                name={current.supermarket_name}
                color={current.supermarket_color}
                emoji={current.supermarket_emoji}
              />
              {current.pack_label && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  {current.pack_label}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100">{current.name}</p>
            <div className="mt-1 flex items-center gap-2">
              <PriceTag
                price={current.price}
                previousPrice={current.previous_price}
                discountPct={current.discount_pct}
                unit={current.unit}
                unitPrice={current.unit_price}
              />
              <button
                onClick={toggleWatch}
                aria-label={isWatching ? "Dejar de avisarme de este precio" : "Avisarme si baja de precio"}
                title={isWatching ? "Dejar de avisarme de este precio" : "Avisarme si baja de precio"}
                className={`press shrink-0 rounded-full p-1.5 text-base transition-colors ${
                  isWatching
                    ? "bg-amber-100 text-amber-500 dark:bg-amber-500/20"
                    : "bg-slate-100 text-slate-300 hover:text-amber-400 dark:bg-slate-800 dark:text-slate-500"
                }`}
              >
                {isWatching ? "🔔" : "🔕"}
              </button>
            </div>
          </div>
        </div>

        <div className="mt-5">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
            También lo tienes en
          </h3>
          {similar === null && (
            <div className="space-y-2">
              <div className="h-12 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
              <div className="h-12 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
            </div>
          )}
          {similar && similar.length === 0 && (
            <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-400 dark:bg-slate-800">
              {current.pack_label
                ? `No hemos encontrado este mismo formato (${current.pack_label}) en otro supermercado todavía.`
                : "No hemos podido identificar el formato exacto de este producto para compararlo."}
            </p>
          )}
          {similar && similar.length > 0 && (
            <div className="space-y-2">
              {similar.map((p) => (
                <button
                  key={p.product_id}
                  onClick={() => setCurrent(p)}
                  className="press flex w-full items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-2.5 text-left shadow-sm transition-colors hover:border-brand-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <SupermarketBadge slug={p.supermarket_slug} name={p.supermarket_name} color={p.supermarket_color} emoji={p.supermarket_emoji} />
                    <span className="truncate text-xs text-slate-500 dark:text-slate-400">{p.name}</span>
                  </div>
                  <span
                    className={`shrink-0 text-sm font-bold ${
                      p.price < current.price
                        ? "text-brand-600 dark:text-brand-400"
                        : "text-slate-800 dark:text-slate-100"
                    }`}
                  >
                    {p.price.toFixed(2)}€
                  </span>
                </button>
              ))}
              {couldSave && (
                <p className="rounded-xl bg-brand-50 p-2.5 text-xs text-brand-800 dark:bg-brand-950 dark:text-brand-200">
                  💡 Ahorrarías {(current.price - cheapestSimilarPrice).toFixed(2)}€ comprando este mismo
                  formato en otro supermercado.
                </p>
              )}
            </div>
          )}
        </div>

        <div className="mt-5">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
            Histórico de precio
          </h3>
          {history === null && (
            <div className="h-32 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
          )}
          {history && history.length <= 1 && (
            <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-400 dark:bg-slate-800">
              Todavía no tenemos suficiente histórico de este producto. Iremos guardando su precio
              cada día para que puedas ver aquí su evolución.
            </p>
          )}
          {history && history.length > 1 && (
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 8, bottom: 0, left: -24 }}>
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    stroke="#94a3b8"
                    domain={["dataMin - 0.1", "dataMax + 0.1"]}
                    tickFormatter={(v) => `${v.toFixed(2)}€`}
                  />
                  <Tooltip formatter={(v) => [`${v.toFixed(2)}€`, "Precio"]} />
                  <Line type="monotone" dataKey="price" stroke="#0d9488" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {current.url && (
          <a
            href={current.url}
            target="_blank"
            rel="noopener noreferrer"
            className="press mt-5 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-white shadow-lg"
            style={{ backgroundColor: current.supermarket_color, boxShadow: `0 8px 20px -6px ${current.supermarket_color}66` }}
          >
            Comprar en {current.supermarket_name} ↗
          </a>
        )}

        <button
          onClick={onClose}
          className="press mt-2 w-full rounded-xl py-2.5 text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}
