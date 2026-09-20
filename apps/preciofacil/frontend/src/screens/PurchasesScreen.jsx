import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";
import SupermarketBadge from "../components/SupermarketBadge.jsx";

const today = () => new Date().toISOString().slice(0, 10);

export default function PurchasesScreen() {
  const { userEmail } = useUser();
  const [categories, setCategories] = useState([]);
  const [supermarkets, setSupermarkets] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    category_slug: "",
    supermarket_slug: "",
    product_name: "",
    price: "",
    purchased_at: today(),
  });

  const loadPurchases = () => {
    api.listPurchases(userEmail).then(setPurchases).catch((err) => setError(err.message));
  };

  useEffect(() => {
    api.categories().then((cats) => {
      setCategories(cats);
      setForm((f) => ({ ...f, category_slug: f.category_slug || cats[0]?.slug || "" }));
    });
    api.supermarkets().then((sm) => {
      setSupermarkets(sm);
      setForm((f) => ({ ...f, supermarket_slug: f.supermarket_slug || sm[0]?.slug || "" }));
    });
    loadPurchases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail]);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.product_name || !form.price) return;
    setSaving(true);
    setError(null);
    try {
      await api.createPurchase({
        user_email: userEmail,
        category_slug: form.category_slug,
        supermarket_slug: form.supermarket_slug,
        product_name: form.product_name,
        price: parseFloat(form.price),
        quantity: 1,
        purchased_at: form.purchased_at,
      });
      setForm((f) => ({ ...f, product_name: "", price: "" }));
      loadPurchases();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    await api.deletePurchase(id, userEmail);
    loadPurchases();
  };

  const smMap = Object.fromEntries(supermarkets.map((s) => [s.slug, s]));
  const catMap = Object.fromEntries(categories.map((c) => [c.slug, c]));

  return (
    <div className="px-4 pt-4">
      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        Registra lo que compras y aprenderemos dónde te sale más a cuenta la próxima vez.
      </p>

      <form
        onSubmit={submit}
        className="mb-6 space-y-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="grid grid-cols-2 gap-2">
          <select
            value={form.category_slug}
            onChange={update("category_slug")}
            className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            {categories.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.icon} {c.label}
              </option>
            ))}
          </select>
          <select
            value={form.supermarket_slug}
            onChange={update("supermarket_slug")}
            className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            {supermarkets.map((s) => (
              <option key={s.slug} value={s.slug}>
                {s.logo_emoji} {s.name}
              </option>
            ))}
          </select>
        </div>
        <input
          placeholder="¿Qué compraste? (ej. Fuet Casademont)"
          value={form.product_name}
          onChange={update("product_name")}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="Precio (€)"
            value={form.price}
            onChange={update("price")}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
          <input
            type="date"
            value={form.purchased_at}
            onChange={update("purchased_at")}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-xl bg-brand-700 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {saving ? "Guardando…" : "Registrar compra"}
        </button>
      </form>

      {error && <p className="mb-3 text-sm text-red-500">{error}</p>}

      <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
        Historial
      </h3>
      <div className="space-y-2">
        {purchases.length === 0 && (
          <p className="text-sm text-slate-400">Todavía no has registrado ninguna compra.</p>
        )}
        {purchases.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                {catMap[p.category_slug]?.icon} {p.product_name}
              </p>
              <div className="mt-1 flex items-center gap-2">
                {smMap[p.supermarket_slug] && (
                  <SupermarketBadge
                    name={smMap[p.supermarket_slug].name}
                    color={smMap[p.supermarket_slug].color}
                    emoji={smMap[p.supermarket_slug].logo_emoji}
                  />
                )}
                <span className="text-xs text-slate-400">{p.purchased_at}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
                {p.price.toFixed(2)}€
              </span>
              <button
                onClick={() => remove(p.id)}
                className="text-slate-300 hover:text-red-500"
                aria-label="Eliminar"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
