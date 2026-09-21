import { useState } from "react";
import { mediaUrl } from "../api.js";

export default function ProductThumb({ src, alt, emoji, className = "" }) {
  const [failed, setFailed] = useState(false);
  const showImage = src && !failed;
  return (
    <div
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-800/60 ${className}`}
    >
      {showImage ? (
        <img
          src={mediaUrl(src)}
          alt={alt}
          className="h-full w-full object-contain"
          onError={() => setFailed(true)}
          loading="lazy"
        />
      ) : (
        <span className="text-2xl">{emoji}</span>
      )}
    </div>
  );
}
