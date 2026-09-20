import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useUser } from "../store.jsx";

export default function SettingsScreen() {
  const { userEmail, setUserEmail } = useUser();
  const [supermarkets, setSupermarkets] = useState([]);
  const [emailDraft, setEmailDraft] = useState(userEmail);

  useEffect(() => {
    api.supermarkets().then(setSupermarkets);
  }, []);

  return (
    <div className="space-y-6 px-4 pt-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
          Tu perfil
        </h3>
        <label className="mb-1 block text-xs text-slate-500">Email</label>
        <div className="flex gap-2">
          <input
            value={emailDraft}
            onChange={(e) => setEmailDraft(e.target.value)}
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
          <button
            onClick={() => setUserEmail(emailDraft)}
            className="rounded-xl bg-brand-700 px-3 py-2 text-sm font-semibold text-white"
          >
            Guardar
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Código postal de referencia: <strong>46022</strong> (Valencia)
        </p>
      </section>

      <section>
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
          Supermercados
        </h3>
        <div className="space-y-2">
          {supermarkets.map((s) => (
            <div
              key={s.slug}
              className="rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-full text-white"
                    style={{ backgroundColor: s.color }}
                  >
                    {s.logo_emoji}
                  </span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {s.name}
                  </span>
                </div>
                {s.live_verified ? (
                  <span className="rounded-full bg-emerald-100 px-2 py-1 text-[10px] font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                    ✓ Precios en vivo
                  </span>
                ) : (
                  <span className="rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                    Sin datos aún
                  </span>
                )}
              </div>
              {s.notes && (
                <p className="mt-2 text-xs text-slate-400">{s.notes}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-400 dark:border-slate-800 dark:bg-slate-900">
        <p>
          Los precios se analizan automáticamente cada día a las 8:00 con
          Crawl4AI. Puedes forzar una actualización manual desde la pestaña
          "Hoy".
        </p>
      </section>
    </div>
  );
}
