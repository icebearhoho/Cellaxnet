"use client";

/**
 * Công tắc ngôn ngữ EN ⇄ VI.
 *
 * Nút nhớ lựa chọn trong localStorage và phát `LANGUAGE_EVENT`;
 * `LanguageProvider` (lib/i18n.tsx) nghe sự kiện đó và cấp ngôn ngữ cho mọi
 * `useT()` bên dưới. Nút không giữ state ngôn ngữ riêng — nó đọc từ provider,
 * để chỉ có một nguồn sự thật.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "@/lib/i18n";

export type Language = "en" | "vi";

const KEY = "area303:lang";
export const LANGUAGE_EVENT = "area303:lang";

export function getLanguage(): Language {
  if (typeof window === "undefined") return "vi";
  try {
    return localStorage.getItem(KEY) === "en" ? "en" : "vi";
  } catch {
    return "vi";
  }
}

function setLanguage(lang: Language): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(KEY, lang);
    window.dispatchEvent(new Event(LANGUAGE_EVENT));
  } catch {
    /* ignore */
  }
}

/* Cờ trong nút thumb — vẽ tay để không phải tải asset ngoài. */

function EarthIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="12" fill="#2f6fb8" />
      <path
        d="M0 12 H24 M12 0 C5 0 5 24 12 24 C19 24 19 0 12 0"
        fill="none"
        stroke="#eaf3fb"
        strokeWidth="1"
      />
      <ellipse cx="7" cy="7" rx="3.6" ry="2.4" fill="#4a9d5f" />
      <ellipse cx="17" cy="16" rx="3" ry="2" fill="#4a9d5f" />
    </svg>
  );
}

/** Ngôi sao 5 cánh, canh giữa trong khung 24×24. */
const STAR_POINTS = (() => {
  const cx = 12, cy = 12.5, rOuter = 9.5, rInner = 3.7;
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? rOuter : rInner;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
  }
  return pts.join(" ");
})();

function StarIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="12" fill="#c8102e" />
      <polygon points={STAR_POINTS} fill="#ffcd00" />
    </svg>
  );
}

const TRACK_W = 74;
const TRACK_H = 32;
const INSET = 3;
const THUMB = TRACK_H - INSET * 2;

export function LanguageToggle() {
  // Ngôn ngữ lấy từ provider, không giữ bản sao ở đây: provider đã đọc
  // localStorage sau khi mount và nghe sự kiện, nên hai bên không thể lệch.
  const lang = useLanguage();
  const [pop, setPop] = useState(false);
  const popTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (popTimer.current) clearTimeout(popTimer.current);
  }, []);

  const toggle = useCallback(() => {
    // Phát sự kiện ngay trong handler, không lồng trong updater của setState:
    // updater chạy trong lúc render, nên sự kiện phát từ đó khiến provider
    // setState giữa render — React báo "Cannot update a component while
    // rendering a different component".
    setLanguage(getLanguage() === "en" ? "vi" : "en");
    setPop(true);
    if (popTimer.current) clearTimeout(popTimer.current);
    popTimer.current = setTimeout(() => setPop(false), 420);
  }, []);

  const isVi = lang === "vi";
  const thumbX = isVi ? TRACK_W - THUMB - INSET : INSET;

  return (
    <button
      type="button"
      onClick={toggle}
      role="switch"
      aria-checked={isVi}
      aria-label={isVi ? "Ngôn ngữ: Tiếng Việt — chuyển sang English" : "Language: English — switch to Vietnamese"}
      title={isVi ? "Tiếng Việt" : "English"}
      className="relative shrink-0 rounded-full border border-border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      style={{
        width: TRACK_W,
        height: TRACK_H,
        // Nền theo cờ: navy (EN) ⇄ đỏ (VI). Đây là màu cờ, cố ý nằm ngoài
        // bảng token của app.
        background: isVi ? "#c8102e" : "#1b2f5e",
        boxShadow: "inset 0 1px 2px rgb(0 0 0 / 0.12)",
      }}
    >
      <span
        className="absolute overflow-hidden rounded-full motion-reduce:transition-none"
        style={{
          top: INSET,
          left: 0,
          width: THUMB,
          height: THUMB,
          transform: `translateX(${thumbX}px)${pop ? " scale(1.08)" : ""}`,
          transition: "transform 480ms cubic-bezier(0.34,1.56,0.64,1)",
          boxShadow: "0 2px 6px rgb(0 0 0 / 0.25)",
        }}
      >
        <span
          className="absolute inset-0 grid place-items-center motion-reduce:transition-none"
          style={{ opacity: isVi ? 0 : 1, transition: "opacity 420ms ease" }}
        >
          <EarthIcon size={THUMB} />
        </span>
        <span
          className="absolute inset-0 grid place-items-center motion-reduce:transition-none"
          style={{ opacity: isVi ? 1 : 0, transition: "opacity 420ms ease" }}
        >
          <StarIcon size={THUMB} />
        </span>
      </span>
    </button>
  );
}
