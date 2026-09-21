import { useState } from "react";
import BottomNav from "./components/BottomNav.jsx";
import OffersScreen from "./screens/OffersScreen.jsx";
import CompareScreen from "./screens/CompareScreen.jsx";
import PurchasesScreen from "./screens/PurchasesScreen.jsx";
import InsightsScreen from "./screens/InsightsScreen.jsx";
import SettingsScreen from "./screens/SettingsScreen.jsx";

const SCREENS = {
  offers: OffersScreen,
  compare: CompareScreen,
  purchases: PurchasesScreen,
  insights: InsightsScreen,
  settings: SettingsScreen,
};

const TITLES = {
  offers: "Ofertas de hoy",
  compare: "Comparar precios",
  purchases: "Mis compras",
  insights: "Tus ahorros",
  settings: "Ajustes",
};

export default function App() {
  const [tab, setTab] = useState("offers");
  const Screen = SCREENS[tab];

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col bg-slate-50 dark:bg-slate-950">
      <header className="safe-top sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-700 text-base text-white">
              🛒
            </span>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wide text-brand-600 dark:text-brand-400">
                PrecioFácil
              </p>
              <h1 className="-mt-0.5 text-base font-bold text-slate-900 dark:text-white">
                {TITLES[tab]}
              </h1>
            </div>
          </div>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-300">
            📍 46022
          </span>
        </div>
      </header>

      <main className="flex-1 pb-24">
        <Screen onNavigate={setTab} />
      </main>

      <BottomNav active={tab} onChange={setTab} />
    </div>
  );
}
