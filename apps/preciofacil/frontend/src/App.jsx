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
    <div className="mx-auto flex min-h-screen max-w-md flex-col">
      <header className="safe-top sticky top-0 z-10 border-b border-slate-200/70 bg-white/80 backdrop-blur-lg dark:border-slate-800/70 dark:bg-slate-900/80">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-base text-white shadow-md shadow-brand-700/30">
              🛒
            </span>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
                PrecioFácil
              </p>
              <h1 className="-mt-0.5 text-base font-bold tracking-tight text-slate-900 dark:text-white">
                {TITLES[tab]}
              </h1>
            </div>
          </div>
          <span className="flex items-center gap-1 rounded-full bg-slate-100/80 px-2.5 py-1 text-xs font-semibold text-slate-500 ring-1 ring-slate-200/70 dark:bg-slate-800/80 dark:text-slate-300 dark:ring-slate-700/70">
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
