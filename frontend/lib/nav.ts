import {
  LayoutDashboard,
  Star,
  Tag,
  ShoppingBag,
  UserMinus,
  TrendingUp,
  Image as ImageIcon,
  MessageSquare,
  PenLine,
  Sparkles,
  ScanFace,
  Heart,
  Users2,
  Truck,
  GraduationCap,
  Route,
  Brain,
  Swords,
  Users,
  Lightbulb,
  Bot,
  ClipboardCheck,
  Network,
  Receipt,
  Store,
  BadgePercent,
  Link2,
  PackagePlus,
  type LucideIcon,
} from "lucide-react";

/**
 * Navigation contract — 17 e-commerce AI/ML features for AREA-303.
 *
 * Slug suffix is the canonical id; appears on every nav row right-aligned in mono.
 * Section groups mirror the day-by-day build plan in the project README.
 */
export type AppKind = "seller" | "shop";

export type NavItem = {
  id: string; // canonical feature id e.g. "01", "17"
  slug: string;
  label: string;
  href: string;
  icon: LucideIcon;
  app: AppKind; // which of the two apps this feature belongs to
  section: "commerce" | "intelligence" | "creator" | "operations" | "demand";
  category:
    | "NLP"
    | "Time Series"
    | "Computer Vision"
    | "Generative AI"
    | "Behavioral AI"
    | "Integration";
  owner: "TL" | "DA" | "FS" | "D1" | "D2";
};

// Two apps: `shop` = buyer storefront, `seller` = seller portal.
// href = /<app>/<slug>. `implemented` features (below) render a live panel.
export const NAV_ITEMS: NavItem[] = [
  // --- SHOP (buyer-facing) ---
  { id: "ST", slug: "store",            label: "Cửa hàng",           href: "/shop/store",            icon: Store,         app: "shop",   section: "commerce",     category: "Behavioral AI",   owner: "FS" },
  { id: "03", slug: "personal-shopper", label: "Trợ lý mua sắm",     href: "/shop/personal-shopper", icon: ShoppingBag,   app: "shop",   section: "commerce",     category: "Generative AI",   owner: "FS" },
  { id: "11", slug: "recsys",           label: "Dành cho bạn",       href: "/shop/recsys",           icon: Sparkles,      app: "shop",   section: "commerce",     category: "Generative AI",   owner: "FS" },
  { id: "07", slug: "visual-search",    label: "Visual Search",      href: "/shop/visual-search",    icon: ImageIcon,     app: "shop",   section: "commerce",     category: "Computer Vision", owner: "DA" },
  { id: "12", slug: "virtual-tryon",    label: "Virtual Try-On",     href: "/shop/virtual-tryon",    icon: ScanFace,      app: "shop",   section: "commerce",     category: "Computer Vision", owner: "DA" },

  // --- SELLER (seller portal) ---
  { id: "AI", slug: "copilot",          label: "Trợ lý vận hành",    href: "/seller/copilot",          icon: Bot,             app: "seller", section: "intelligence", category: "Generative AI",   owner: "TL" },
  { id: "AP", slug: "autopilot",        label: "Digital Twin",      href: "/seller/autopilot",        icon: Sparkles,        app: "seller", section: "intelligence", category: "Generative AI",   owner: "TL" },
  { id: "VB", slug: "voucher-booster",  label: "Voucher Booster",   href: "/seller/voucher-booster",  icon: BadgePercent,    app: "seller", section: "commerce",     category: "Generative AI",   owner: "TL" },
  { id: "BR", slug: "daily-briefing",   label: "Hôm nay cần làm gì",  href: "/seller/daily-briefing",   icon: ClipboardCheck,  app: "seller", section: "intelligence", category: "Generative AI",   owner: "TL" },
  { id: "01", slug: "review-intelligence", label: "Đánh giá khách hàng", href: "/seller/review-intelligence", icon: Star, app: "seller", section: "intelligence", category: "NLP", owner: "DA" },
  { id: "OD", slug: "orders",           label: "Đơn hàng",           href: "/seller/orders",           icon: Receipt,       app: "seller", section: "commerce",     category: "Behavioral AI",   owner: "TL" },
  { id: "02", slug: "dynamic-pricing",  label: "Gợi ý giá bán",    href: "/seller/dynamic-pricing",  icon: Tag,           app: "seller", section: "commerce",     category: "Time Series",     owner: "TL" },
  { id: "04", slug: "customer-risk",    label: "Rủi ro khách hàng",  href: "/seller/customer-risk",    icon: UserMinus,     app: "seller", section: "intelligence", category: "Behavioral AI",   owner: "TL" },
  { id: "06", slug: "demand-forecast",  label: "Demand Forecast",    href: "/seller/demand-forecast",  icon: TrendingUp,    app: "seller", section: "intelligence", category: "Time Series",     owner: "DA" },
  { id: "13", slug: "emotion-sale",     label: "Ưu đãi giữ chân",    href: "/seller/emotion-sale",     icon: Heart,         app: "seller", section: "intelligence", category: "Behavioral AI",   owner: "D1" },
  { id: "50", slug: "segmentation",     label: "Nhóm khách hàng", href: "/seller/segmentation",     icon: Users2,        app: "seller", section: "intelligence", category: "Behavioral AI",   owner: "D1" },
  { id: "09", slug: "content-generator",label: "Nội dung sản phẩm",  href: "/seller/content-generator",icon: PenLine,       app: "seller", section: "creator",      category: "Generative AI",   owner: "FS" },
  { id: "17", slug: "seller-coach",     label: "Cải thiện cửa hàng", href: "/seller/seller-coach",     icon: GraduationCap, app: "seller", section: "creator",      category: "Generative AI",   owner: "FS" },
  { id: "08", slug: "sentiment-alert",  label: "Cảnh báo nhu cầu",    href: "/seller/sentiment-alert",  icon: MessageSquare, app: "seller", section: "creator",      category: "NLP",              owner: "D1" },
  { id: "16", slug: "supply-chain",     label: "Rủi ro vận chuyển",       href: "/seller/supply-chain",     icon: Truck,         app: "seller", section: "operations",   category: "Time Series",     owner: "TL" },
  { id: "23", slug: "restock-planner",  label: "Kế hoạch nhập hàng",      href: "/seller/restock-planner",  icon: PackagePlus,   app: "seller", section: "operations",   category: "Time Series",     owner: "D1" },
  { id: "24", slug: "marketplace",      label: "Kết nối bán hàng",        href: "/seller/marketplace",      icon: Link2,          app: "seller", section: "operations",   category: "Integration",     owner: "D1" },
  { id: "18", slug: "product-knowledge",    label: "Biến động sản phẩm",   href: "/seller/product-knowledge",    icon: Brain,     app: "seller", section: "intelligence", category: "Generative AI", owner: "TL" },
  { id: "19", slug: "market-intelligence",  label: "So sánh đối thủ", href: "/seller/market-intelligence",  icon: Swords,    app: "seller", section: "intelligence", category: "Generative AI", owner: "TL" },
  { id: "20", slug: "creator-performance",  label: "Hiệu quả nhà sáng tạo", href: "/seller/creator-performance",  icon: Users,     app: "seller", section: "creator",      category: "Generative AI", owner: "TL" },
  { id: "21", slug: "decision-intelligence",label: "Hỗ trợ quyết định",href:"/seller/decision-intelligence",icon: Lightbulb, app: "seller", section: "intelligence", category: "Generative AI", owner: "TL" },
  { id: "22", slug: "product-graph",       label: "Quan hệ sản phẩm",       href: "/seller/product-graph",        icon: Network,   app: "seller", section: "intelligence", category: "Generative AI", owner: "TL" },

  // --- Bonus (Track 1 official brief, not part of the 17-idea brainstorm) ---
  { id: "T1-2", slug: "customer-journey", label: "Hành trình khách",   href: "/seller/customer-journey", icon: Route,         app: "seller", section: "intelligence", category: "Behavioral AI",   owner: "FS" },
];

/** Features that have a live, wired panel (vs. a placeholder). */
export const IMPLEMENTED = new Set<string>([
  "autopilot",
  "voucher-booster",
  "virtual-tryon",
  "personal-shopper", "recsys", "content-generator", "seller-coach",
  "orders",
  "review-intelligence", "dynamic-pricing", "customer-risk", "customer-journey",
  "sentiment-alert", "supply-chain",
  "emotion-sale", "segmentation",
  "product-knowledge", "market-intelligence", "creator-performance", "decision-intelligence",
  "product-graph",
  "restock-planner", "marketplace",
  "copilot", "daily-briefing",
]);

/** Routes that are useful to end users today. Keep unfinished concepts out of navigation. */
export const READY_NAV_ITEMS = NAV_ITEMS.filter(
  (item) => item.slug === "store" || IMPLEMENTED.has(item.slug),
);

/** Tenant-safe tools available to a normal seller before legacy APIs are scoped. */
export const SELLER_SELF_SERVICE_SLUGS = new Set(["autopilot", "voucher-booster", "orders", "copilot"]);

/** Analytical modules feed Digital Twin; they are no longer equal-level destinations. */
const SELLER_PRODUCT_SLUGS = new Set(["autopilot", "voucher-booster", "orders", "copilot"]);

export function navForApp(app: AppKind): NavItem[] {
  return READY_NAV_ITEMS.filter(
    (item) => item.app === app && (app !== "seller" || SELLER_PRODUCT_SLUGS.has(item.slug)),
  );
}

/**
 * Which base role an app requires, or null when it's open to everyone.
 *
 * Kept per-app rather than per-NavItem: all seller features share one
 * identical rule, so copies of `role: "seller"` would just be something to
 * drift out of sync. If per-feature permissions are ever needed, add an
 * optional `requiresRole` to NavItem and filter inside navForApp().
 */
export const APP_REQUIRED_ROLE: Record<AppKind, "seller" | null> = {
  shop: null,
  seller: "seller",
};

export function canAccessApp(app: AppKind, role: string | null | undefined): boolean {
  const required = APP_REQUIRED_ROLE[app];
  return required === null || role === required || role === "admin";
}

export const SUBTITLE: Record<string, string> = {
  "autopilot": "Digital Twin hợp nhất tín hiệu shop thành quyết định có thể mô phỏng, duyệt và theo dõi.",
  "voucher-booster": "Mô phỏng, kiểm tra biên lợi nhuận và duyệt ưu đãi trước khi đưa lên Shopee hoặc TikTok Shop.",
  "virtual-tryon": "Tải ảnh của bạn và thử trang phục bằng mô hình CatVTON.",
  "copilot": "Trợ lý vận hành cửa hàng.",
  "daily-briefing": "Việc ưu tiên theo tác động doanh thu",
  "personal-shopper": "Tìm sản phẩm theo nhu cầu và ngân sách.",
  "recsys": "Sản phẩm phù hợp với bạn.",
  "content-generator": "Viết nội dung sản phẩm cho các sàn.",
  "seller-coach": "Kiểm tra cửa hàng và đề xuất cải thiện.",
  "review-intelligence": "Tổng hợp cảm xúc và phát hiện đánh giá đáng ngờ.",
  "dynamic-pricing": "Đề xuất giá bán cạnh tranh dựa trên trung vị các sản phẩm cùng danh mục.",
  "customer-risk": "Khách có nguy cơ rời đi, hoàn trả, hối hận — và ai đang rủi ro chồng cần can thiệp gấp.",
  "customer-journey": "Xem lại hành trình và bước tiếp theo của khách.",
  "sentiment-alert": "Kết hợp buzz mạng xã hội với tồn kho để cảnh báo sớm trước khi sản phẩm viral gây hết hàng.",
  "supply-chain": "Cảnh báo sớm gián đoạn chuỗi cung ứng (bão, ùn tắc cảng) theo khu vực kho hàng.",
  "emotion-sale": "Phát hiện khách 'thích nhưng do dự' từ tín hiệu hành vi và kích hoạt ưu đãi cá nhân hoá đúng lúc.",
  "segmentation": "Nhóm khách hàng theo hành vi mua sắm.",
  "product-knowledge": "Giải thích vì sao doanh số thay đổi — bóc tách các yếu tố tác động (giá, khuyến mãi, traffic, tồn kho).",
  "market-intelligence": "Phân tích đối thủ & giá — so sánh vị thế và đề xuất mức giá tối ưu không phá sàn lợi nhuận.",
  "creator-performance": "Đo hiệu quả KOL/KOC theo doanh số quy đổi, doanh số/1k view và tỷ lệ tương tác.",
  "decision-intelligence": "Học từ quyết định quá khứ để rút ra hành động nên lặp lại và thời điểm chạy ads tốt nhất.",
  "product-graph": "Quan hệ SKU/brand + sản phẩm tương tự",
  "orders": "Đơn hàng thật do khách đặt — xác nhận, giao hoặc hủy.",
  "restock-planner": "Phân bổ ngân sách nhập hàng theo mùa vụ, nhu cầu và áp lực khuyến mãi trên thị trường.",
  "marketplace": "Kết nối và theo dõi trạng thái đồng bộ dữ liệu từ các sàn bán hàng.",
};

export const NAV_SECTIONS: Array<{ id: NavItem["section"]; title: string }> = [
  { id: "commerce",    title: "Bán hàng" },
  { id: "intelligence",title: "Phân tích" },
  { id: "creator",     title: "Nội dung" },
  { id: "operations",  title: "Vận hành" },
];

export const SECTION_TITLES: Record<NavItem["section"], string> = {
  commerce: "Commerce",
  intelligence: "Intelligence",
  creator: "Creator",
  operations: "Operations",
  demand: "Demand",
};

/** Quick lookup by slug for the dynamic page fallback. */
export function findBySlug(slug: string): NavItem | undefined {
  return NAV_ITEMS.find((i) => i.slug === slug);
}
