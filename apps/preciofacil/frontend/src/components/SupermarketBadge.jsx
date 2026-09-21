import SupermarketLogo from "./SupermarketLogo.jsx";

export default function SupermarketBadge({ slug, name, color, emoji, size = "sm" }) {
  const padding = size === "sm" ? "py-0.5 pl-0.5 pr-2 text-xs" : "py-1 pl-1 pr-3 text-sm";
  const iconSize = size === "sm" ? "h-4 w-4" : "h-5 w-5";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold text-white shadow-sm ${padding}`}
      style={{ backgroundColor: color }}
    >
      <SupermarketLogo slug={slug} color={color} emoji={emoji} className={iconSize} />
      {name}
    </span>
  );
}
