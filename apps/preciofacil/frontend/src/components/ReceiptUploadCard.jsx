import { useRef, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";

const today = () => new Date().toISOString().slice(0, 10);

export default function ReceiptUploadCard({ categories, supermarkets, onConfirmed }) {
  const { userEmail } = useUser();
  const fileInputRef = useRef(null);
  const [status, setStatus] = useState("idle"); // idle | analyzing | reviewing | confirming
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState(null);
  const [supermarketSlug, setSupermarketSlug] = useState("");
  const [purchasedAt, setPurchasedAt] = useState(today());
  const [items, setItems] = useState([]);

  const reset = () => {
    setStatus("idle");
    setDraft(null);
    setItems([]);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("analyzing");
    setError(null);
    try {
      const result = await api.analyzeReceipt(file);
      setDraft(result);
      setSupermarketSlug(result.supermarket_slug || supermarkets[0]?.slug || "");
      setPurchasedAt(result.purchase_date || today());
      setItems(
        result.items.map((it, idx) => ({
          key: idx,
          product_name: it.name,
          category_slug: it.category_slug || "",
          price: it.unit_price,
          quantity: it.quantity,
        }))
      );
      setStatus("reviewing");
    } catch (err) {
      setError(err.message);
      setStatus("idle");
    }
  };

  const updateItem = (key, field) => (e) => {
    const value = field === "product_name" ? e.target.value : field === "category_slug" ? e.target.value : parseFloat(e.target.value) || 0;
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, [field]: value } : it)));
  };

  const removeItem = (key) => setItems((prev) => prev.filter((it) => it.key !== key));

  const total = items.reduce((acc, it) => acc + it.price * it.quantity, 0);
  const missingCategory = items.some((it) => !it.category_slug);
  const canConfirm = items.length > 0 && !missingCategory && supermarketSlug && !!purchasedAt;

  const handleConfirm = async () => {
    setStatus("confirming");
    setError(null);
    try {
      await api.confirmReceipt({
        user_email: userEmail,
        supermarket_slug: supermarketSlug,
        purchased_at: purchasedAt,
        receipt_image_path: draft.receipt_image_path,
        items: items.map((it) => ({
          product_name: it.product_name,
          category_slug: it.category_slug,
          price: it.price,
          quantity: it.quantity,
        })),
      });
      onConfirmed?.();
      reset();
    } catch (err) {
      setError(err.message);
      setStatus("reviewing");
    }
  };

  if (status === "idle") {
    return (
      <div className="mb-6">
        <label className="press flex cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-slate-300 bg-white/60 py-4 text-sm font-semibold text-slate-500 transition-colors hover:border-brand-400 hover:text-brand-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400">
          📷 Escanear ticket de compra
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleFile}
          />
        </label>
        {error && (
          <p className="mt-2 rounded-xl bg-red-50 p-2.5 text-xs text-red-600 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}
      </div>
    );
  }

  if (status === "analyzing") {
    return (
      <div className="mb-6 flex items-center justify-center gap-2 rounded-2xl border border-slate-200/70 bg-white p-6 text-sm text-slate-500 shadow-sm dark:border-slate-800/70 dark:bg-slate-900 dark:text-slate-400">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        Analizando el ticket con IA…
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm dark:border-slate-800/70 dark:bg-slate-900">
      <h3 className="mb-1 text-sm font-bold text-slate-800 dark:text-slate-100">
        Revisa el ticket antes de guardarlo
      </h3>
      <p className="mb-3 text-xs text-slate-400">
        Corrige lo que haga falta — la IA puede equivocarse. Nada se guarda hasta que confirmes.
      </p>

      {draft?.warning && (
        <p className="mb-3 rounded-xl bg-amber-50 p-2.5 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300">
          {draft.warning}
        </p>
      )}

      <div className="mb-3 grid grid-cols-2 gap-2">
        <select
          value={supermarketSlug}
          onChange={(e) => setSupermarketSlug(e.target.value)}
          className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        >
          <option value="" disabled>
            Supermercado…
          </option>
          {supermarkets.map((s) => (
            <option key={s.slug} value={s.slug}>
              {s.logo_emoji} {s.name}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={purchasedAt}
          onChange={(e) => setPurchasedAt(e.target.value)}
          className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      </div>

      <div className="space-y-2">
        {items.length === 0 && (
          <p className="text-xs text-slate-400">No hay productos que registrar de este ticket.</p>
        )}
        {items.map((it) => (
          <div
            key={it.key}
            className="rounded-xl border border-slate-200/70 bg-slate-50/60 p-2.5 dark:border-slate-800/70 dark:bg-slate-800/40"
          >
            <div className="flex items-center gap-2">
              <input
                value={it.product_name}
                onChange={updateItem(it.key, "product_name")}
                className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              />
              <button
                onClick={() => removeItem(it.key)}
                className="press shrink-0 text-slate-300 hover:text-red-500"
                aria-label="Quitar"
              >
                ✕
              </button>
            </div>
            <div className="mt-1.5 grid grid-cols-3 gap-1.5">
              <select
                value={it.category_slug}
                onChange={updateItem(it.key, "category_slug")}
                className={`rounded-lg border bg-white px-1.5 py-1 text-xs dark:bg-slate-900 dark:text-slate-100 ${
                  it.category_slug
                    ? "border-slate-200 dark:border-slate-700"
                    : "border-red-300 dark:border-red-700"
                }`}
              >
                <option value="" disabled>
                  Categoría…
                </option>
                {categories.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.icon} {c.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="0.01"
                min="0"
                value={it.price}
                onChange={updateItem(it.key, "price")}
                className="rounded-lg border border-slate-200 bg-white px-1.5 py-1 text-xs dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              />
              <input
                type="number"
                step="1"
                min="1"
                value={it.quantity}
                onChange={updateItem(it.key, "quantity")}
                className="rounded-lg border border-slate-200 bg-white px-1.5 py-1 text-xs dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-slate-500 dark:text-slate-400">Total</span>
        <span className="font-bold text-slate-800 dark:text-slate-100">{total.toFixed(2)}€</span>
      </div>

      {missingCategory && (
        <p className="mt-2 text-xs text-red-500">
          Elige una categoría para cada producto antes de confirmar.
        </p>
      )}
      {error && (
        <p className="mt-2 rounded-xl bg-red-50 p-2.5 text-xs text-red-600 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mt-3 flex gap-2">
        <button
          onClick={reset}
          className="press flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-500 dark:border-slate-700 dark:text-slate-400"
        >
          Cancelar
        </button>
        <button
          onClick={handleConfirm}
          disabled={!canConfirm || status === "confirming"}
          className="press flex-[2] rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 py-2.5 text-sm font-semibold text-white shadow-md shadow-brand-700/25 disabled:opacity-50"
        >
          {status === "confirming" ? "Guardando…" : `Confirmar ${items.length} compra${items.length === 1 ? "" : "s"}`}
        </button>
      </div>
    </div>
  );
}
