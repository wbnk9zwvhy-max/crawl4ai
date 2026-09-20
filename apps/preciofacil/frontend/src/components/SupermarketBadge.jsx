export default function SupermarketBadge({ name, color, emoji, size = "sm" }) {
  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-semibold text-white ${padding}`}
      style={{ backgroundColor: color }}
    >
      <span>{emoji}</span>
      {name}
    </span>
  );
}
