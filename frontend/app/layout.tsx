import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Patrick_Hand } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { AuthProvider } from "@/lib/auth-context";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const patrickHand = Patrick_Hand({
  weight: "400",
  subsets: ["latin", "vietnamese"],
  variable: "--font-doodle",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AREA-303 — Operations",
  description: "Operations dashboard for AREA-303.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="vi"
      className={`${inter.variable} ${jetbrainsMono.variable} ${patrickHand.variable}`}
    >
      <head>
        {/* Đặt theme TRƯỚC khi trang vẽ. Nếu để React làm sau khi mount thì
            người chọn giao diện tối sẽ thấy một nháy sáng trắng trước khi
            chuyển — lỗi này gọi là "flash of wrong theme", và cách duy nhất
            tránh được là chạy đồng bộ ngay trong <head>. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem("area303:theme")==="dark")document.documentElement.setAttribute("data-theme","dark")}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-screen bg-bg text-text antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
