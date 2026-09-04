import { ExternalLink, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Marketplace = {
  id: "shopee" | "lazada" | "tiktok" | "tiki";
  name: string;
  description: string;
  sellerUrl: string;
  buttonClassName: string;
  logoSrc: string;
};

const MARKETPLACES: Marketplace[] = [
  {
    id: "shopee",
    name: "Shopee",
    description: "Đăng nhập Seller Centre để chọn gian hàng Shopee của bạn.",
    sellerUrl: "https://banhang.shopee.vn/account/signin",
    buttonClassName: "border-[#bd341b] bg-[#ee4d2d] hover:bg-[#dc4327]",
    logoSrc: "/marketplaces/shopee.png",
  },
  {
    id: "lazada",
    name: "Lazada",
    description: "Đăng nhập Seller Center để chọn gian hàng Lazada của bạn.",
    sellerUrl: "https://sellercenter.lazada.vn/apps/seller/login?login=1",
    buttonClassName: "border-[#16106d] bg-[#241b91] hover:bg-[#1d167d]",
    logoSrc: "/marketplaces/lazada.png",
  },
  {
    id: "tiktok",
    name: "TikTok Shop",
    description: "Đăng nhập Seller Center để chọn gian hàng TikTok Shop của bạn.",
    sellerUrl: "https://seller-vn.tiktok.com/account/welcome",
    buttonClassName: "border-black bg-[#11131c] hover:bg-black",
    logoSrc: "/marketplaces/tiktok-shop.png",
  },
  {
    id: "tiki",
    name: "Tiki",
    description: "Đăng nhập Seller Center để chọn gian hàng Tiki của bạn.",
    sellerUrl: "https://sellercenter.tiki.vn/",
    buttonClassName: "border-[#075dbb] bg-[#1677ff] hover:bg-[#0868d8]",
    logoSrc: "/marketplaces/tiki.png",
  },
];

export function MarketplacePanel() {
  return (
    <Card className="overflow-hidden hover:translate-y-0 hover:shadow-none">
      <CardHeader className="border-b border-border bg-surface/70 px-5 py-4 sm:px-6">
        <div>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <Link2 className="h-4 w-4 text-accent" />
            Kết nối sàn bán hàng
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Chọn sàn để mở Seller Center và đăng nhập gian hàng của bạn.
          </p>
        </div>
      </CardHeader>

      <CardContent className="p-5 sm:p-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {MARKETPLACES.map((marketplace) => (
            <article
              key={marketplace.id}
              className="group flex min-h-[270px] flex-col items-center rounded-xl border border-border bg-surface px-4 py-5 text-center shadow-[2px_3px_0_hsl(var(--text)/calc(0.08*var(--shadow-strength)))] transition duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-[4px_6px_0_hsl(var(--text)/calc(0.11*var(--shadow-strength)))]"
            >
              <div className="h-20 w-40 transition-transform duration-200 group-hover:scale-105">
                {/* Keep the original marketplace image bytes; optimization would transform the supplied logos. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={marketplace.logoSrc}
                  alt={`Logo ${marketplace.name}`}
                  className="h-full w-full object-contain"
                />
              </div>

              <h3 className="mt-4 text-lg font-bold text-text">{marketplace.name}</h3>
              <p className="mt-1.5 max-w-[240px] text-sm leading-5 text-text-muted">
                {marketplace.description}
              </p>

              <Button
                asChild
                size="md"
                className={`mt-auto w-full text-white ${marketplace.buttonClassName}`}
              >
                <a
                  href={marketplace.sellerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Kết nối ${marketplace.name} trong tab mới`}
                >
                  Kết nối
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
