import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import ProductThumb from "./ProductThumb.jsx";
import SupermarketBadge from "./SupermarketBadge.jsx";
import PriceTag from "./PriceTag.jsx";

const dateFormatter = new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "short" });

export default function ProductDetailSheet({ product, categoryIcon, onClose }) {
  const [history, setHistory] = useState(null);

  useEffect(() => {
    setHistory(null);
    api
      .productHistory(product.product_id)
      .then((points) =>
        setHistory(points.map((p) => ({ ...p, label: dateFormatter.format(new Date(p.scraped_at)) })))
      )
      .catch(() => setHistory([]));
  }, [product.product_id]);

  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/40" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-t-3xl bg-white p-4 pb-8 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-slate-200 dark:bg-slate-700" />

        <div className="flex gap-3">
          <ProductThumb src={product.image_url} alt={product.name} emoji={categoryIcon} className="h-20 w-20" />
          <div className="min-w-0 flex-1">
            <SupermarketBadge
              slug={product.supermarket_slug}
              name={product.supermarket_name}
              color={product.supermarket_color}
              emoji={product.supermarket_emoji}
            />
            <p className="mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100">{product.name}</p>
            <div className="mt-1">
              <PriceTag
                price={product.price}
                previousPrice={product.previous_price}
                discountPct={product.discount_pct}
                unit={product.unit}
                unitPrice={product.unit_price}
              />
            </div>
          </div>
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

        {product.url && (
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-white"
            style={{ backgroundColor: product.supermarket_color }}
          >
            Comprar en {product.supermarket_name} ↗
          </a>
        )}

        <button
          onClick={onClose}
          className="mt-2 w-full rounded-xl py-2.5 text-sm font-semibold text-slate-500 dark:text-slate-400"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}
