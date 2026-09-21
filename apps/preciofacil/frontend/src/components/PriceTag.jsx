export default function PriceTag({ price, previousPrice, discountPct, unit, unitPrice }) {
  return (
    <div className="flex flex-wrap items-baseline gap-1.5">
      <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
        {price.toFixed(2)}€
      </span>
      {previousPrice ? (
        <span className="text-sm text-slate-400 line-through decoration-slate-300 dark:decoration-slate-600">
          {previousPrice.toFixed(2)}€
        </span>
      ) : null}
      {discountPct ? (
        <span className="rounded-md bg-gradient-to-br from-accent-500 to-accent-600 px-1.5 py-0.5 text-xs font-bold text-white shadow-sm shadow-accent-600/30">
          -{Math.round(discountPct)}%
        </span>
      ) : null}
      {unitPrice && unit ? (
        <span className="text-xs text-slate-400">
          ({unitPrice.toFixed(2)}€/{unit})
        </span>
      ) : null}
    </div>
  );
}
