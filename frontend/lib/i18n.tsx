"use client";

/**
 * Dịch giao diện EN ⇄ VI.
 *
 * Giao diện được viết bằng tiếng Việt trước, nên tiếng Việt là *nguồn*, không
 * phải một bản dịch: khoá tra cứu chính là câu tiếng Việt. Cách này đổi lấy vẻ
 * gọn gàng của khoá dạng `pricing.headline` để lấy hai thứ đáng hơn ở quy mô
 * này — không phải sửa 59 file để đặt tên khoá, và một chuỗi chưa dịch vẫn hiển
 * thị đúng tiếng Việt thay vì hiện ra `pricing.headline` giữa màn hình demo.
 *
 * Dùng:
 *
 *     const t = useT();
 *     <p>{t("Gợi ý giá bán")}</p>
 *
 * Khi ngôn ngữ là "vi", `t` trả lại nguyên chuỗi. Khi là "en", nó tra trong
 * `EN`; không thấy thì vẫn trả tiếng Việt và ghi log ở môi trường dev, để chuỗi
 * bị bỏ sót lộ ra trong lúc phát triển chứ không phải lúc trình bày.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { EN } from "@/lib/i18n-en";
import { LANGUAGE_EVENT, getLanguage, type Language } from "@/components/shell/language-toggle";

const LanguageContext = createContext<Language>("vi");

/** Đặt quanh cây component để mọi `useT()` bên dưới cùng đọc một ngôn ngữ. */
export function LanguageProvider({ children }: { children: React.ReactNode }) {
  // Luôn khởi tạo "vi": server không đọc được localStorage, nếu render đầu đã
  // là "en" thì markup hai bên lệch nhau và React sẽ báo hydration mismatch.
  const [lang, setLang] = useState<Language>("vi");

  useEffect(() => {
    setLang(getLanguage());

    const sync = () => setLang(getLanguage());
    window.addEventListener(LANGUAGE_EVENT, sync);
    // Đổi ngôn ngữ ở tab khác cũng phải áp dụng ở đây.
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(LANGUAGE_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return <LanguageContext.Provider value={lang}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): Language {
  return useContext(LanguageContext);
}

const missing = new Set<string>();

/** Hàm dịch. Nhận câu tiếng Việt, trả câu theo ngôn ngữ đang chọn. */
export function useT(): (vi: string) => string {
  const lang = useLanguage();

  return useCallback(
    (vi: string): string => {
      if (lang === "vi") return vi;
      const en = EN[vi];
      if (en !== undefined) return en;

      if (process.env.NODE_ENV !== "production" && !missing.has(vi)) {
        missing.add(vi);
        console.warn("[i18n] thiếu bản dịch:", JSON.stringify(vi));
      }
      return vi;
    },
    [lang],
  );
}

/** Dịch câu có chỗ trống rồi mới điền giá trị vào.
 *
 *  Dịch khung trước, chèn sau — nếu ghép số vào rồi mới tra thì câu đã có số
 *  bên trong sẽ không bao giờ khớp một khoá cố định nào. Chỗ trống đặt tên
 *  (`{giá}`) chứ không theo thứ tự, vì tiếng Anh và tiếng Việt sắp xếp thành
 *  phần câu khác nhau nên bản dịch phải được phép đảo thứ tự.
 *
 *      const tf = useTf();
 *      tf("Không nên bán dưới {sàn}.", { sàn: "125.000₫" })
 */
export function useTf(): (template: string, values: Record<string, string | number>) => string {
  const t = useT();
  return useCallback(
    (template: string, values: Record<string, string | number>): string =>
      t(template).replace(/\{(\w+)\}/g, (whole, key: string) =>
        key in values ? String(values[key]) : whole,
      ),
    [t],
  );
}

/**
 * Bản dịch ngoài component (hằng số ở đầu module, hàm tiện ích).
 *
 * Không phải hook nên đọc localStorage trực tiếp — chỉ dùng khi thật sự không
 * gọi được `useT()`, vì nó không kích hoạt render lại khi đổi ngôn ngữ.
 */
export function translate(vi: string): string {
  if (getLanguage() === "vi") return vi;
  return EN[vi] ?? vi;
}
