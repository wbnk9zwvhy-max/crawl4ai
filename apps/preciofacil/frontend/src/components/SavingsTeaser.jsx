import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";

export default function SavingsTeaser({ onNavigate }) {
  const { userEmail } = useUser();
  const [insights, setInsights] = useState(null);

  useEffect(() => {
    api
      .insights(userEmail)
      .then(setInsights)
      .catch(() => setInsights([]));
  }, [userEmail]);

  if (!insights || insights.length === 0) return null;

  const total = insights.reduce((acc, i) => acc + i.savings_amount, 0);

  return (
    <button
      onClick={() => onNavigate?.("insights")}
      className="press relative mb-5 flex w-full items-center justify-between gap-3 overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-600 to-brand-800 p-4 text-left text-white shadow-lg shadow-brand-700/25"
    >
      <div
        className="pointer-events-none absolute -right-6 -top-10 h-32 w-32 rounded-full bg-white/10 blur-xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-8 left-10 h-20 w-20 rounded-full bg-accent-500/20 blur-2xl"
        aria-hidden="true"
      />
      <div className="relative">
        <p className="text-xs font-semibold uppercase tracking-wider text-brand-100">
          Podrías ahorrar
        </p>
        <p className="text-3xl font-extrabold tracking-tight">{total.toFixed(2)}€</p>
        <p className="mt-0.5 text-xs text-brand-100">
          según lo que sueles comprar · toca para ver el detalle
        </p>
      </div>
      <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/15 text-2xl ring-1 ring-white/25">
        💡
      </span>
    </button>
  );
}
