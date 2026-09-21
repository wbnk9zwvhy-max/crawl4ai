import { useState } from "react";

const LOGO_EXT = { dia: "svg" };

export default function SupermarketLogo({ slug, color, emoji, className = "h-8 w-8" }) {
  const [failed, setFailed] = useState(false);
  const logoSrc = slug ? `/logos/${slug}.${LOGO_EXT[slug] || "png"}` : null;
  const showLogo = logoSrc && !failed;

  return (
    <span
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-white ${className}`}
      style={!showLogo ? { backgroundColor: color } : undefined}
    >
      {showLogo ? (
        <img
          src={logoSrc}
          alt=""
          className="h-full w-full object-contain"
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="text-white">{emoji}</span>
      )}
    </span>
  );
}
