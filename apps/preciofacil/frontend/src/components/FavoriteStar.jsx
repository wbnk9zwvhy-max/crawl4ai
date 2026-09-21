export default function FavoriteStar({ active, onToggle, size = "text-base" }) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      aria-label={active ? "Quitar de favoritos" : "Marcar como favorito"}
      className={`press shrink-0 ${size} ${active ? "text-amber-400" : "text-slate-300 hover:text-amber-300"}`}
    >
      {active ? "★" : "☆"}
    </button>
  );
}
