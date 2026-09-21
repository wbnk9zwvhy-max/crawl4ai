const TABS = [
  { id: "offers", label: "Hoy", icon: "🔥" },
  { id: "compare", label: "Comparar", icon: "⚖️" },
  { id: "purchases", label: "Mis compras", icon: "🧾" },
  { id: "spending", label: "Gasto", icon: "📊" },
  { id: "insights", label: "Ahorros", icon: "💡" },
  { id: "settings", label: "Ajustes", icon: "⚙️" },
];

export default function BottomNav({ active, onChange }) {
  return (
    <nav className="safe-bottom fixed inset-x-0 bottom-0 z-20 border-t border-slate-200/70 bg-white/85 backdrop-blur-lg shadow-[0_-4px_20px_-8px_rgba(15,23,42,0.15)] dark:border-slate-800/70 dark:bg-slate-900/85">
      <div className="mx-auto flex max-w-md justify-between px-2 py-1.5">
        {TABS.map((tab) => {
          const isActive = tab.id === active;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={`press flex flex-1 flex-col items-center gap-0.5 rounded-xl px-1 py-1.5 text-[11px] font-medium transition-colors ${
                isActive
                  ? "text-brand-700 dark:text-brand-300"
                  : "text-slate-400 dark:text-slate-500"
              }`}
            >
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full text-base transition-all duration-200 ${
                  isActive
                    ? "bg-gradient-to-br from-brand-100 to-brand-200 shadow-sm dark:from-brand-900 dark:to-brand-800"
                    : ""
                }`}
              >
                {tab.icon}
              </span>
              {tab.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
