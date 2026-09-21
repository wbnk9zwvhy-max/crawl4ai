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
      className="mb-5 flex w-full items-center justify-between gap-3 rounded-2xl bg-gradient-to-br from-brand-700 to-brand-500 p-4 text-left text-white"
    >
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-brand-100">
          Podrías ahorrar
        </p>
        <p className="text-2xl font-extrabold">{total.toFixed(2)}€</p>
        <p className="mt-0.5 text-xs text-brand-100">
          según lo que sueles comprar · toca para ver el detalle
        </p>
      </div>
      <span className="text-2xl">💡</span>
    </button>
  );
}
