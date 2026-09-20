export default function PriceTag({ price, previousPrice, discountPct, unit, unitPrice }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-lg font-extrabold text-slate-900 dark:text-white">
        {price.toFixed(2)}€
      </span>
      {previousPrice ? (
        <span className="text-sm text-slate-400 line-through">{previousPrice.toFixed(2)}€</span>
      ) : null}
      {discountPct ? (
        <span className="rounded-md bg-accent-500 px-1.5 py-0.5 text-xs font-bold text-white">
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
