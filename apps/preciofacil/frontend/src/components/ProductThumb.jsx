import { useState } from "react";
import { mediaUrl } from "../api.js";

export default function ProductThumb({ src, alt, emoji, className = "" }) {
  const [failed, setFailed] = useState(false);
  const showImage = src && !failed;
  return (
    <div
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-slate-50 dark:bg-slate-800 ${className}`}
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
