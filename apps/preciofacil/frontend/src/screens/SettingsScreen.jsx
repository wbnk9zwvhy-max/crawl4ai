import { useEffect, useState } from "react";
import { api } from "../api.js";
import { getExistingSubscription, pushSupported, subscribeToPush, unsubscribeFromPush } from "../push.js";
import { useUser } from "../store.jsx";
import SupermarketLogo from "../components/SupermarketLogo.jsx";

export default function SettingsScreen() {
  const { userEmail, setUserEmail } = useUser();
  const [supermarkets, setSupermarkets] = useState([]);
  const [emailDraft, setEmailDraft] = useState(userEmail);
  const [pushState, setPushState] = useState("checking"); // checking | unsupported | unavailable | off | on
  const [pushBusy, setPushBusy] = useState(false);
  const [pushError, setPushError] = useState(null);
  const [pushMessage, setPushMessage] = useState(null);

  useEffect(() => {
    api.supermarkets().then(setSupermarkets);
  }, []);

  useEffect(() => {
    if (!pushSupported()) {
      setPushState("unsupported");
      return;
    }
    api
      .vapidPublicKey()
      .then(() =>
        getExistingSubscription()
          .then((sub) => setPushState(sub ? "on" : "off"))
          .catch(() => setPushState("off"))
      )
      .catch(() => setPushState("unavailable"));
  }, []);

  const handleEnablePush = async () => {
    setPushBusy(true);
    setPushError(null);
    setPushMessage(null);
    try {
      await subscribeToPush(userEmail);
      setPushState("on");
    } catch (err) {
      setPushError(err.message);
    } finally {
      setPushBusy(false);
    }
  };

  const handleDisablePush = async () => {
    setPushBusy(true);
    setPushError(null);
    setPushMessage(null);
    try {
      await unsubscribeFromPush(userEmail);
      setPushState("off");
    } catch (err) {
      setPushError(err.message);
    } finally {
      setPushBusy(false);
    }
  };

  const handleTestPush = async () => {
    setPushBusy(true);
    setPushError(null);
    setPushMessage(null);
    try {
      await api.testPush(userEmail);
      setPushMessage("Notificación de prueba enviada. Debería llegarte en unos segundos.");
    } catch (err) {
      setPushError(err.message);
    } finally {
      setPushBusy(false);
    }
  };

  return (
    <div className="space-y-6 px-4 pt-4">
      <section className="rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
          Tu perfil
        </h3>
        <label className="mb-1 block text-xs text-slate-500">Email</label>
        <div className="flex gap-2">
          <input
            value={emailDraft}
            onChange={(e) => setEmailDraft(e.target.value)}
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm transition-colors focus:border-brand-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
          <button
            onClick={() => setUserEmail(emailDraft)}
            className="press rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 px-3 py-2 text-sm font-semibold text-white shadow-md shadow-brand-700/25"
          >
            Guardar
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Código postal de referencia: <strong>46022</strong> (Valencia)
        </p>
      </section>

      <section className="rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
          Notificaciones
        </h3>
        <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
          Recibe un aviso en tu móvil en cuanto baje de precio (o toque mínimo histórico) algún
          producto que estés vigilando con 🔔, sin tener que abrir la app.
        </p>

        {pushState === "checking" && <p className="text-xs text-slate-400">Comprobando...</p>}
        {pushState === "unsupported" && (
          <p className="text-xs text-slate-400">
            Tu navegador no admite notificaciones push. Prueba desde Chrome/Edge en Android o
            instalando la app en la pantalla de inicio en iOS 16.4+.
          </p>
        )}
        {pushState === "unavailable" && (
          <p className="text-xs text-slate-400">
            Las notificaciones push no están activadas en este servidor todavía.
          </p>
        )}
        {(pushState === "off" || pushState === "on") && (
          <div className="flex flex-wrap items-center gap-2">
            {pushState === "off" && (
              <button
                onClick={handleEnablePush}
                disabled={pushBusy}
                className="press rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 px-3 py-2 text-xs font-semibold text-white shadow-md shadow-brand-700/25 disabled:opacity-50"
              >
                {pushBusy ? "Activando…" : "🔔 Activar notificaciones"}
              </button>
            )}
            {pushState === "on" && (
              <>
                <span className="rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
                  ✓ Activadas
                </span>
                <button
                  onClick={handleTestPush}
                  disabled={pushBusy}
                  className="press rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
                >
                  Enviar prueba
                </button>
                <button
                  onClick={handleDisablePush}
                  disabled={pushBusy}
                  className="press rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-500 disabled:opacity-50 dark:border-slate-700 dark:text-slate-400"
                >
                  Desactivar
                </button>
              </>
            )}
          </div>
        )}
        {pushError && <p className="mt-2 text-xs text-red-500">{pushError}</p>}
        {pushMessage && <p className="mt-2 text-xs text-emerald-600 dark:text-emerald-400">{pushMessage}</p>}
      </section>

      <section>
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
          Supermercados
        </h3>
        <div className="space-y-2">
          {supermarkets.map((s) => (
            <div
              key={s.slug}
              className="rounded-2xl border border-slate-200/70 bg-white p-3 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800/70 dark:bg-slate-900"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SupermarketLogo slug={s.slug} color={s.color} emoji={s.logo_emoji} className="h-9 w-9" />
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {s.name}
                  </span>
                </div>
                {s.live_verified ? (
                  <span className="rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
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

      <section className="rounded-2xl border border-slate-200/70 bg-white/90 p-4 text-xs text-slate-400 shadow-sm backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/90">
        <p>
          Los precios se analizan automáticamente cada día a las 8:00 con
          Crawl4AI. Puedes forzar una actualización manual desde la pestaña
          "Hoy".
        </p>
      </section>
    </div>
  );
}
