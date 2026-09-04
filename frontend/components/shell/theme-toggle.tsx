"use client";

/**
 * Công tắc giao diện Sáng ⇄ Tối.
 *
 * App KHÔNG đi theo cài đặt màu của hệ điều hành: mặc định luôn là sáng, máy
 * để chế độ tối thì app vẫn mở ra sáng. Chế độ tối chỉ bật khi người dùng tự
 * chọn, và lựa chọn đó được nhớ lại.
 *
 * Lựa chọn ghi vào thuộc tính `data-theme` trên <html>; bảng màu tối trong
 * globals.css đọc thuộc tính đó. Chọn sáng thì *xoá* thuộc tính đi — không có
 * `data-theme` nghĩa là dùng bảng màu mặc định trong `:root`.
 *
 * Việc đặt theme lần đầu do script trong app/layout.tsx làm, chạy trước khi
 * trang vẽ — nếu để React làm sau khi mount thì người chọn nền tối sẽ thấy một
 * nháy sáng trước khi chuyển.
 */

import { useCallback, useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

export type Theme = "light" | "dark";

const KEY = "area303:theme";
export const THEME_EVENT = "area303:theme";

export function getTheme(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    return localStorage.getItem(KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

/** Ghi lựa chọn và áp dụng ngay lên <html>. */
function setTheme(theme: Theme): void {
  if (typeof window === "undefined") return;
  try {
    if (theme === "dark") {
      localStorage.setItem(KEY, "dark");
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      localStorage.removeItem(KEY);
      document.documentElement.removeAttribute("data-theme");
    }
    window.dispatchEvent(new Event(THEME_EVENT));
  } catch {
    /* ignore */
  }
}

//: Biểu tượng và nhãn mô tả trạng thái SẼ chuyển sang khi bấm, không phải
//: trạng thái hiện tại — đó mới là thứ người dùng cần biết trước khi bấm.
const META: Record<Theme, { icon: typeof Sun; label: string }> = {
  light: { icon: Moon, label: "Chuyển sang giao diện tối" },
  dark: { icon: Sun, label: "Chuyển sang giao diện sáng" },
};

export function ThemeToggle() {
  // Khởi tạo "light" rồi đọc sau khi mount: server không thấy localStorage,
  // đọc ngay lúc render đầu sẽ làm markup hai bên lệch nhau.
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    setThemeState(getTheme());

    // Đổi ở tab khác cũng phải áp dụng ở đây.
    const sync = () => setThemeState(getTheme());
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);

  const toggle = useCallback(() => {
    const next: Theme = getTheme() === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }, []);

  const { icon: Icon, label } = META[theme];

  return (
    <button
      type="button"
      onClick={toggle}
      title={label}
      aria-label={label}
      className={cn(
        "grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border",
        "bg-surface-2 text-text-muted transition-colors",
        "hover:border-border-strong hover:text-text",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        "focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
      )}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
    </button>
  );
}
