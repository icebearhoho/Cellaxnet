/**
 * Mock data — AREA-303 e-commerce domain.
 * Deterministic so charts hydrate identically on the server and client.
 *
 * Domains:
 * - KPIS: today's revenue, orders, conversion, AOV
 * - TIMESERIES: hourly GMV across 3 categories for the last 24h
 * - ALERTS: cross-feature alerts (returns, fake review, low stock, churn spike, sentiment drop)
 * - PROVINCES: 63 Vietnam provinces for supply-chain risk heatmap (idea #16)
 * - PRODUCTS: small fixture used by #03 Personal Shopper, #09 Content Generator, #11 RecSys
 */

export type SeriesPoint = { t: string; v: number };

export type Kpi = {
  id: string;
  label: string;
  value: number;
  unit?: string;
  delta: number; // percent, signed
  spark: number[];
  /** When true, a downward delta is the "good" outcome. */
  inverted?: boolean;
};

export const KPIS: Kpi[] = [
  {
    id: "revenue",
    label: "Doanh thu hôm nay",
    value: 184_230_000,
    unit: "₫",
    delta: 12.4,
    spark: [120, 132, 128, 141, 152, 148, 160, 158, 167, 172, 170, 184].map((m) => m * 1_000_000),
  },
  {
    id: "orders",
    label: "Đơn hàng hôm nay",
    value: 2_847,
    delta: 8.6,
    spark: [1.8, 2.0, 1.9, 2.1, 2.3, 2.2, 2.4, 2.5, 2.6, 2.7, 2.75, 2.85].map((m) => m * 1000),
  },
  {
    id: "conversion",
    label: "Tỷ lệ chuyển đổi",
    value: 3.42,
    unit: "%",
    delta: 0.4,
    spark: [3.0, 3.1, 3.05, 3.15, 3.2, 3.18, 3.25, 3.28, 3.32, 3.36, 3.4, 3.42],
  },
  {
    id: "aov",
    label: "Giá trị đơn trung bình",
    value: 487_000,
    unit: "₫",
    delta: -1.8,
    inverted: false,
    spark: [510, 505, 502, 498, 495, 492, 490, 489, 488, 488, 487, 487].map((m) => m * 1000),
  },
];

/** Hourly GMV (₫ million) for last 24h, by top-level category. */
export const TIMESERIES: Array<{ t: string; fashion: number; beauty: number; accessories: number }> =
  Array.from({ length: 24 }, (_, i) => {
    const hour = String(i).padStart(2, "0");
    const base = (h: number) => 80 + Math.sin((h + i) / 3) * 32 + (h % 6) * 4;
    return {
      t: `${hour}:00`,
      fashion: Math.round(base(3) * 10) / 10,
      beauty: Math.round(base(5) * 10) / 10 - 18,
      accessories: Math.round(base(7) * 10) / 10 - 32,
    };
  });

export type AlertSeverity = "critical" | "warning" | "info";
export type AlertStatus = "open" | "monitoring" | "resolved";
export type AlertSource =
  | "review-intelligence"
  | "customer-risk"
  | "supply-chain"
  | "sentiment-alert";

export type Alert = {
  id: string;
  feature: AlertSource;
  featureLabel: string;
  region: string;
  severity: AlertSeverity;
  status: AlertStatus;
  startedAt: string;
  message: string;
};

export const ALERTS: Alert[] = [
  {
    id: "ALT-2407",
    feature: "customer-risk",
    featureLabel: "Rủi ro khách hàng",
    region: "Hà Nội",
    severity: "critical",
    status: "open",
    startedAt: "2026-07-08 03:42",
    message: "Áo khoác denim cỡ M — tỷ lệ hoàn hàng 28%, gấp đôi mức thông thường",
  },
  {
    id: "ALT-2406",
    feature: "customer-risk",
    featureLabel: "Rủi ro khách hàng",
    region: "TP.HCM",
    severity: "warning",
    status: "monitoring",
    startedAt: "2026-07-08 02:18",
    message: "Nhóm khách có nguy cơ rời bỏ tăng 14% trong 24 giờ — 312 khách hàng",
  },
  {
    id: "ALT-2405",
    feature: "sentiment-alert",
    featureLabel: "Cảnh báo cảm xúc",
    region: "Đà Nẵng",
    severity: "info",
    status: "resolved",
    startedAt: "2026-07-07 23:51",
    message: "Phản hồi tiêu cực về 'giao hàng chậm' tăng đột biến — 47 lượt nhắc trong 1 giờ",
  },
  {
    id: "ALT-2404",
    feature: "supply-chain",
    featureLabel: "Chuỗi cung ứng",
    region: "Bắc Ninh",
    severity: "warning",
    status: "open",
    startedAt: "2026-07-07 22:09",
    message: "Kho tổng Bắc Ninh — dự báo son môi sẽ hết hàng trong 5 ngày",
  },
  {
    id: "ALT-2403",
    feature: "review-intelligence",
    featureLabel: "Phân tích đánh giá",
    region: "—",
    severity: "info",
    status: "resolved",
    startedAt: "2026-07-07 19:30",
    message: "Phát hiện 23 đánh giá rác trên trang sản phẩm serum vitamin C",
  },
];

/** 63 Vietnam provinces (centroids) — supply chain #16 heatmap. */
export type ProvinceNode = {
  id: string;
  name: string;
  region: "north" | "central" | "south";
  lat: number;
  lng: number;
  status: "ok" | "warn" | "critical";
  load: number; // 0..1 supply chain risk
};

export const PROVINCES: ProvinceNode[] = [
  { id: "p-hn",  name: "Hà Nội",       region: "north",   lat: 21.0285,  lng: 105.8542,  status: "ok",       load: 0.42 },
  { id: "p-hcm", name: "TP.HCM",       region: "south",   lat: 10.8231,  lng: 106.6297,  status: "warn",     load: 0.74 },
  { id: "p-dn",  name: "Đà Nẵng",      region: "central", lat: 16.0544,  lng: 108.2022,  status: "ok",       load: 0.38 },
  { id: "p-hp",  name: "Hải Phòng",    region: "north",   lat: 20.8449,  lng: 106.6881,  status: "ok",       load: 0.51 },
  { id: "p-ct",  name: "Cần Thơ",      region: "south",   lat: 10.0452,  lng: 105.7469,  status: "ok",       load: 0.34 },
  { id: "p-bn",  name: "Bắc Ninh",     region: "north",   lat: 21.1861,  lng: 106.0763,  status: "critical", load: 0.91 },
  { id: "p-bd",  name: "Bình Dương",   region: "south",   lat: 11.3254,  lng: 106.4770,  status: "warn",     load: 0.78 },
  { id: "p-dn2", name: "Đồng Nai",     region: "south",   lat: 10.9574,  lng: 106.8426,  status: "ok",       load: 0.55 },
  { id: "p-la",  name: "Long An",      region: "south",   lat: 10.6956,  lng: 106.2431,  status: "ok",       load: 0.46 },
  { id: "p-tt",  name: "Thừa Thiên Huế",region: "central", lat: 16.4637,  lng: 107.5909,  status: "ok",       load: 0.40 },
  { id: "p-kh",  name: "Khánh Hòa",    region: "central", lat: 12.2388,  lng: 109.1967,  status: "ok",       load: 0.36 },
  { id: "p-ls",  name: "Lâm Đồng",     region: "central", lat: 11.5753,  lng: 108.1429,  status: "ok",       load: 0.32 },
];

/* ------------------------------------------------------------------ */
/* Fixture products — used by Personal Shopper / RecSys / Content Gen */
/* ------------------------------------------------------------------ */

export type Product = {
  id: string;
  name: string;
  brand: string;
  category: "Thời trang" | "Mỹ phẩm" | "Phụ kiện";
  platform: "Shopee" | "Tiki" | "TikTok Shop";
  priceVnd: number;
  rating: number;
  reviews: number;
  similarity?: number; // 0..1, used by visual search and recsys
  imageHue: number; // 0..360 — synthesized swatch, deterministic
  imageUrl?: string; // real product photo; falls back to icon when empty
  description: string;
};

// Tiki CDN product photos — same map as backend `demo_data._PRODUCT_IMAGES`
// so RecSys / Personal Shopper / Store share consistent catalog imagery.
const PRODUCT_IMAGES: Record<string, string> = {
  polo: "https://salt.tikicdn.com/cache/280x280/ts/product/1f/92/47/3bf7e43d1a4a909601a3abddd7cc19ee.jpg",
  dress_shirt: "https://salt.tikicdn.com/cache/280x280/ts/product/00/4e/0d/d5a4d4377729ca891ace108e545dc4f5.jpg",
  tshirt: "https://salt.tikicdn.com/cache/280x280/ts/product/b5/c1/93/90b8ba8e894db21a6c71a781202f1421.jpg",
  hoodie: "https://salt.tikicdn.com/cache/280x280/ts/product/f4/29/35/590921289b459569b9733adb0cf1cd5d.jpg",
  bomber_jacket: "https://salt.tikicdn.com/cache/280x280/ts/product/d1/0b/54/0787b8fd1f3cc408e093e85433dc47b5.jpg",
  denim_jacket: "https://salt.tikicdn.com/cache/280x280/ts/product/d2/1b/23/2d908dedbbb7d21a1d9f4d0599b42511.jpg",
  knitwear: "https://salt.tikicdn.com/cache/280x280/ts/product/d2/ed/a6/8d672991bc29e141ca411b459e1cdb3b.jpg",
  winter_coat: "https://salt.tikicdn.com/cache/280x280/ts/product/6b/70/1a/7cb328d8b1787e797c282335beac76d6.jpg",
  blazer: "https://salt.tikicdn.com/cache/280x280/ts/product/03/a8/05/cab44ca4741ab95b4ff17ee4d3f2ee43.jpg",
  jogger: "https://salt.tikicdn.com/cache/280x280/ts/product/41/da/94/af279036fc2fd4b263aa6bcc061eebbb.jpg",
  shorts: "https://salt.tikicdn.com/cache/280x280/ts/product/0e/50/7a/e220b835b8653637d1a9950e761320fe.png",
  jeans: "https://salt.tikicdn.com/cache/280x280/ts/product/a4/c5/3a/899cdaaed1874ee8c00524c5d7e9e269.jpg",
  leggings: "https://salt.tikicdn.com/cache/280x280/ts/product/4f/3d/b0/799b8f0120cc15024af1f8b32a5f93fb.jpg",
  skirt: "https://salt.tikicdn.com/cache/280x280/ts/product/9d/92/8e/09d967370fd4de808e8c0972130b878a.png",
  dress: "https://salt.tikicdn.com/cache/280x280/ts/product/21/c4/fc/bcdb27da2082a5b6ebcefdcd3999d955.jpg",
  sneakers: "https://salt.tikicdn.com/cache/280x280/ts/product/f3/89/cb/972f0726ef4b4e128176ef01051321a8.jpg",
  boots: "https://salt.tikicdn.com/cache/280x280/ts/product/1c/8e/49/1080a94340c12ee2e428331c5087faf1.jpeg",
  sandals: "https://salt.tikicdn.com/cache/280x280/ts/product/07/ba/2b/db637a555bef5b7be027356087672174.jpg",
  lipstick: "https://salt.tikicdn.com/cache/280x280/ts/product/12/ff/1d/7f2418faf53502dc31a69095815b1864.jpg",
  serum: "https://salt.tikicdn.com/cache/280x280/ts/product/bd/20/ae/d2325cb41ce023ca708232b3315940be.jpg",
  moisturizer: "https://salt.tikicdn.com/cache/280x280/ts/product/0e/7c/53/e730aa98f95bedd2753de95367515b18.png",
  sunscreen: "https://salt.tikicdn.com/cache/280x280/ts/product/54/04/ed/806b70fec51463a302ee57e361049064.jpg",
  foundation: "https://salt.tikicdn.com/cache/280x280/ts/product/1c/31/14/eb7c32a4236bf73fe815e855f0dcd9cf.jpg",
  toner: "https://salt.tikicdn.com/cache/280x280/ts/product/d2/95/4f/cc9f7d61dd9a8a8d8dd5eac78a68b2bf.jpg",
  eyeshadow: "https://salt.tikicdn.com/cache/280x280/ts/product/9c/c3/e1/4ead17820b2c0992f7e8ea0e1d42468f.jpg",
  mascara: "https://salt.tikicdn.com/cache/280x280/ts/product/49/f9/83/b5aaea1b6f97dcd18132c8839a48729e.jpg",
  blush: "https://salt.tikicdn.com/cache/280x280/ts/product/b8/a0/61/3ba36a6f299762970ae56d1d7dfc8fc0.png",
  perfume: "https://salt.tikicdn.com/cache/280x280/ts/product/01/61/55/08525c6ff5034a9ccbe5495eaa9899d2.jpg",
  face_mask: "https://salt.tikicdn.com/cache/280x280/ts/product/c1/3b/92/93a88c230bc1fba5bd0aa2d0648b5ad3.jpg",
  face_wash: "https://salt.tikicdn.com/cache/280x280/ts/product/a4/d6/b3/c2637f1105a8fc3d232812e0e3d38561.png",
  handbag: "https://salt.tikicdn.com/cache/280x280/ts/product/cb/52/9f/d97ef63258d9c79dce12a08eff3718c0.PNG",
  tote_bag: "https://salt.tikicdn.com/cache/280x280/ts/product/e5/21/9e/05fa9414afae9bce11503326dac015ee.jpg",
  crossbody_bag: "https://salt.tikicdn.com/cache/280x280/ts/product/ad/f1/b6/2ad59cf9888c28cddf6780b77a255f64.PNG",
  backpack: "https://salt.tikicdn.com/cache/280x280/ts/product/07/59/2f/efc5263b83456776466b67351668ad31.png",
  wallet: "https://salt.tikicdn.com/cache/280x280/ts/product/16/26/54/444523b65575e0e90ace430477ee0bb4.jpg",
  sunglasses: "https://salt.tikicdn.com/cache/280x280/ts/product/d1/02/57/816bd74884726910f904f5d3f2c5be97.jpg",
  cap: "https://salt.tikicdn.com/cache/280x280/ts/product/de/82/f7/3b7a598d562117ef01bbf83fdd292c41.jpg",
  watch: "https://salt.tikicdn.com/cache/280x280/ts/product/e2/01/46/10adc7c87e995232a86596a744bc888a.jpg",
  necklace: "https://salt.tikicdn.com/cache/280x280/ts/product/e9/e5/9d/7133a234155897a85ca519e9211397d8.jpg",
  bracelet: "https://salt.tikicdn.com/cache/280x280/ts/product/0a/b8/7b/70056be8ca9f810be223e2599b05ec24.png",
  earrings: "https://salt.tikicdn.com/cache/280x280/ts/product/67/45/5e/3b56fa91b600fc9f694497e2c314397b.jpg",
  scarf: "https://salt.tikicdn.com/cache/280x280/ts/product/a5/94/57/513f2a07227304a6095a14d256c95e13.png",
  pajamas: "https://salt.tikicdn.com/cache/280x280/ts/product/4e/f9/1b/a21111c4f916e276d044855f2e940ff3.png",
  default: "https://salt.tikicdn.com/cache/280x280/ts/product/b5/c1/93/90b8ba8e894db21a6c71a781202f1421.jpg",
};

/** Resolve a catalog-style product photo from name + category (demo imagery). */
export function getMockImageUrl(name: string, category: string): string {
  const n = `${name} ${category}`.toLowerCase();
  const has = (...ks: string[]) => ks.some((k) => n.includes(k));

  // Thời trang
  if (has("áo polo", "polo")) return PRODUCT_IMAGES.polo;
  if (has("áo sơ mi", "sơ mi")) return PRODUCT_IMAGES.dress_shirt;
  if (has("áo thun", "áo phông", "thun", "oversize")) return PRODUCT_IMAGES.tshirt;
  if (has("hoodie", "áo hoodie")) return PRODUCT_IMAGES.hoodie;
  if (has("áo khoác bomber", "bomber")) return PRODUCT_IMAGES.bomber_jacket;
  if (has("áo khoác denim", "denim", "áo khoác")) return PRODUCT_IMAGES.denim_jacket;
  if (has("áo len", "cardigan", "áo vest", "blazer")) return PRODUCT_IMAGES.knitwear;
  if (has("áo dạ", "áo phao", "down jacket")) return PRODUCT_IMAGES.winter_coat;
  if (has("áo vest", "blazer")) return PRODUCT_IMAGES.blazer;
  if (has("quần jogger", "jogger", "quần baggy", "baggy")) return PRODUCT_IMAGES.jogger;
  if (has("quần short", "short")) return PRODUCT_IMAGES.shorts;
  if (has("quần", "jean", "denim")) return PRODUCT_IMAGES.jeans;
  if (has("váy", "đầm", "dress", "midi")) return has("đầm") ? PRODUCT_IMAGES.dress : PRODUCT_IMAGES.skirt;
  if (has("giày", "sneaker", "dép", "sandal")) return has("sandal") ? PRODUCT_IMAGES.sandals : PRODUCT_IMAGES.sneakers;
  if (has("boots", "boot")) return PRODUCT_IMAGES.boots;

  // Mỹ phẩm
  if (has("son", "tint", "lipstick")) return PRODUCT_IMAGES.lipstick;
  if (has("serum", "vitamin c", "bha", "aha", "tinh chất", "essence")) return PRODUCT_IMAGES.serum;
  if (has("mặt nạ", "mask", "laneige", "sleeping")) return PRODUCT_IMAGES.face_mask;
  if (has("kem", "cream", "dưỡng", "lotion", "cushion")) return PRODUCT_IMAGES.moisturizer;
  if (has("toner", "rửa mặt", "sữa rửa", "sữa tắm")) return PRODUCT_IMAGES.face_wash;
  if (has("chống nắng", "anessa", "spf")) return PRODUCT_IMAGES.sunscreen;
  if (has("nước hoa", "perfume", "fragrance")) return PRODUCT_IMAGES.perfume;
  if (has("phấn", "makeup")) return PRODUCT_IMAGES.foundation;
  if (has("mascara", "eyeliner", "kẻ mắt")) return PRODUCT_IMAGES.mascara;
  if (has("phấn má", "blush", "highlighter")) return PRODUCT_IMAGES.blush;

  // Phụ kiện
  if (has("túi", "tote", "bag", "balo")) {
    if (has("tote")) return PRODUCT_IMAGES.tote_bag;
    if (has("đeo chéo", "chéo")) return PRODUCT_IMAGES.crossbody_bag;
    if (has("balo")) return PRODUCT_IMAGES.backpack;
    return PRODUCT_IMAGES.handbag;
  }
  if (has("kính", "sunglass", "mát")) return PRODUCT_IMAGES.sunglasses;
  if (has("đồng hồ", "casio", "watch")) return PRODUCT_IMAGES.watch;
  if (has("ví", "wallet")) return PRODUCT_IMAGES.wallet;
  if (has("dây chuyền", "necklace")) return PRODUCT_IMAGES.necklace;
  if (has("vòng tay", "bracelet", "lắc")) return PRODUCT_IMAGES.bracelet;
  if (has("bông tai", " earrings", "hoa tai")) return PRODUCT_IMAGES.earrings;
  if (has("khăn", "scarf", "choàng")) return PRODUCT_IMAGES.scarf;
  if (has("mũ", "nón", "cap")) return PRODUCT_IMAGES.cap;

  return PRODUCT_IMAGES.default;
}

const PRODUCTS_BASE: Product[] = [
  {
    id: "P001",
    name: "Áo khoác denim unisex form rộng",
    brand: "Local Brand X",
    category: "Thời trang",
    platform: "Shopee",
    priceVnd: 489_000,
    rating: 4.6,
    reviews: 1284,
    similarity: 0.92,
    imageHue: 215,
    imageUrl: "https://picsum.photos/seed/denim-jacket/400/400",
    description:
      "Denim 12oz wash nhẹ, form rộng unisex, 2 túi ngực + 2 túi hông. Phù hợp đi học, đi chơi.",
  },
  {
    id: "P002",
    name: "Serum Vitamin C 15% NUDESTIX",
    brand: "NUDESTIX",
    category: "Mỹ phẩm",
    platform: "Tiki",
    priceVnd: 720_000,
    rating: 4.4,
    reviews: 892,
    similarity: 0.88,
    imageHue: 45,
    imageUrl: "https://picsum.photos/seed/serum/400/400",
    description:
      "Serum C ổn định, sáng da, giảm thâm sau 4 tuần. Dùng buổi sáng, kết hợp kem chống nắng.",
  },
  {
    id: "P003",
    name: "Túi tote canvas in họa tiết",
    brand: "OEM",
    category: "Phụ kiện",
    platform: "TikTok Shop",
    priceVnd: 159_000,
    rating: 4.7,
    reviews: 3201,
    similarity: 0.81,
    imageHue: 160,
    imageUrl: "https://picsum.photos/seed/handbag/400/400",
    description:
      "Tote canvas dày 12oz, in lụa 2 mặt, đường chỉ gấp đôi. Chứa laptop 14 inch.",
  },
  {
    id: "P004",
    name: "Son tint lì Bourjois Velvet 21",
    brand: "Bourjois",
    category: "Mỹ phẩm",
    platform: "Shopee",
    priceVnd: 295_000,
    rating: 4.5,
    reviews: 612,
    similarity: 0.76,
    imageHue: 350,
    imageUrl: "https://picsum.photos/seed/lipstick/400/400",
    description:
      "Tint lì lâu trôi 8h, finish velvet không khô môi. Tông 21 — đỏ gạch.",
  },
  {
    id: "P005",
    name: "Quần ống rộng lưng cao linen",
    brand: "Local Brand Y",
    category: "Thời trang",
    platform: "Tiki",
    priceVnd: 369_000,
    rating: 4.3,
    reviews: 458,
    similarity: 0.73,
    imageHue: 35,
    imageUrl: "https://picsum.photos/seed/jeans/400/400",
    description:
      "Linen pha, lưng cao che bụng, ống rộng xếp ly. Size S–XL.",
  },
  {
    id: "P006",
    name: "Mặt nạ ngủ Laneige Water Sleeping Mask",
    brand: "Laneige",
    category: "Mỹ phẩm",
    platform: "Shopee",
    priceVnd: 650_000,
    rating: 4.8,
    reviews: 2410,
    similarity: 0.69,
    imageHue: 200,
    imageUrl: "https://picsum.photos/seed/face-mask/400/400",
    description:
      "Mặt nạ ngủ cấp ẩm 8h, dùng sau serum. Phù hợp da khô, da hỗn hợp.",
  },
  {
    id: "P007",
    name: "Đồng hồ Casio MTP-V002 minimal",
    brand: "Casio",
    category: "Phụ kiện",
    platform: "TikTok Shop",
    priceVnd: 489_000,
    rating: 4.7,
    reviews: 1803,
    similarity: 0.65,
    imageHue: 0,
    imageUrl: "https://picsum.photos/seed/watch/400/400",
    description:
      "Mặt tròn 38mm, dây thép không gỉ, chống nước 30m. Bảo hành 1 năm.",
  },
  {
    id: "P008",
    name: "Áo thun oversize cotton 220gsm",
    brand: "Local Brand Z",
    category: "Thời trang",
    platform: "Shopee",
    priceVnd: 189_000,
    rating: 4.5,
    reviews: 5210,
    similarity: 0.60,
    imageHue: 270,
    imageUrl: "https://picsum.photos/seed/tshirt/400/400",
    description:
      "Cotton 220gsm dày dặn, form oversize, in lụa không bong. 5 màu.",
  },
  {
    id: "P009",
    name: "Sữa rửa mặt CeraVe cho da dầu mụn",
    brand: "CeraVe",
    category: "Mỹ phẩm",
    platform: "Tiki",
    priceVnd: 285_000,
    rating: 4.6,
    reviews: 1543,
    similarity: 0.58,
    imageHue: 180,
    imageUrl: "https://picsum.photos/seed/face-wash/400/400",
    description:
      "Sữa rửa mặt tạo bọt, kiểm soát dầu, chứa ceramide + niacinamide. Da dầu, da mụn.",
  },
  {
    id: "P010",
    name: "Kem chống nắng Anessa SPF50+ PA++++",
    brand: "Anessa",
    category: "Mỹ phẩm",
    platform: "Shopee",
    priceVnd: 520_000,
    rating: 4.7,
    reviews: 2890,
    similarity: 0.55,
    imageHue: 50,
    imageUrl: "https://picsum.photos/seed/sunscreen/400/400",
    description:
      "Chống nắng kiềm dầu, không bết, phù hợp da dầu mụn. Dùng bước cuối buổi sáng.",
  },
  {
    id: "P011",
    name: "Toner BHA Paula's Choice 2%",
    brand: "Paula's Choice",
    category: "Mỹ phẩm",
    platform: "Tiki",
    priceVnd: 610_000,
    rating: 4.5,
    reviews: 876,
    similarity: 0.52,
    imageHue: 120,
    imageUrl: "https://picsum.photos/seed/toner/400/400",
    description:
      "BHA 2% giảm mụn ẩn, thông thoáng lỗ chân lông. Da dầu, da mụn nhẹ.",
  },
  {
    id: "P012",
    name: "Kem dưỡng ẩm gel không dầu Neutrogena",
    brand: "Neutrogena",
    category: "Mỹ phẩm",
    platform: "Shopee",
    priceVnd: 240_000,
    rating: 4.3,
    reviews: 1120,
    similarity: 0.48,
    imageHue: 90,
    imageUrl: "https://picsum.photos/seed/moisturizer/400/400",
    description:
      "Gel dưỡng ẩm oil-free cấp nước, không gây bít tắc. Hợp da dầu mụn.",
  },
  {
    id: "P013",
    name: "Cushion trang điểm kiềm dầu 3CE",
    brand: "3CE",
    category: "Mỹ phẩm",
    platform: "TikTok Shop",
    priceVnd: 430_000,
    rating: 4.4,
    reviews: 654,
    similarity: 0.45,
    imageHue: 330,
    imageUrl: "https://picsum.photos/seed/foundation/400/400",
    description:
      "Cushion finish lì, kiềm dầu 8h, SPF35. Tông tự nhiên cho da dầu.",
  },
  {
    id: "P014",
    name: "Váy đầm midi cổ vuông tay bồng",
    brand: "Local Brand W",
    category: "Thời trang",
    platform: "Shopee",
    priceVnd: 359_000,
    rating: 4.2,
    reviews: 312,
    similarity: 0.42,
    imageHue: 280,
    imageUrl: "https://picsum.photos/seed/dress/400/400",
    description:
      "Đầm midi cổ vuông, tay bồng, vải tuyết mưa. Đi tiệc, đi làm. Size S–L.",
  },
  {
    id: "P015",
    name: "Giày sneaker trắng đế cao 4cm",
    brand: "Local Brand V",
    category: "Thời trang",
    platform: "Tiki",
    priceVnd: 429_000,
    rating: 4.1,
    reviews: 287,
    similarity: 0.38,
    imageHue: 0,
    imageUrl: "https://picsum.photos/seed/sneakers/400/400",
    description:
      "Sneaker da PU trắng, đế cao 4cm tôn dáng, lót êm. Size 35–43.",
  },
  {
    id: "P016",
    name: "Quần jean nữ ống suông lưng cao",
    brand: "Local Brand U",
    category: "Thời trang",
    platform: "Shopee",
    priceVnd: 329_000,
    rating: 4.4,
    reviews: 543,
    similarity: 0.35,
    imageHue: 220,
    imageUrl: "https://picsum.photos/seed/jeans/400/400",
    description:
      "Jean cotton co giãn nhẹ, ống suông, lưng cao. Xanh wash cổ điển.",
  },
  {
    id: "P017",
    name: "Kính mát nữ gọng vuông trendy",
    brand: "OEM",
    category: "Phụ kiện",
    platform: "TikTok Shop",
    priceVnd: 149_000,
    rating: 4.0,
    reviews: 1876,
    similarity: 0.32,
    imageHue: 60,
    imageUrl: "https://picsum.photos/seed/sunglasses/400/400",
    description:
      "Gọng acetate vuông, tròng chống UV400. Nhiều màu, kèm hộp + khăn.",
  },
  {
    id: "P018",
    name: "Balo laptop chống nước 15.6 inch",
    brand: "OEM",
    category: "Phụ kiện",
    platform: "Shopee",
    priceVnd: 259_000,
    rating: 4.5,
    reviews: 2109,
    similarity: 0.30,
    imageHue: 150,
    imageUrl: "https://picsum.photos/seed/backpack/400/400",
    description:
      "Balo chống nước, ngăn laptop 15.6 inch có đệm, cổng sạc USB. Đi học/đi làm.",
  },
];

export const PRODUCTS: Product[] = PRODUCTS_BASE.map((p) => ({
  ...p,
  imageUrl: getMockImageUrl(p.name, p.category),
}));

/* Personal Shopper quick-prompt chips — Vietnamese. */
export const SHOPPER_CHIPS = [
  "Quà sinh nhật cho bạn nữ 25 tuổi, tầm 500k",
  "Son môi tự nhiên cho da ngăm",
  "Đồ đi làm công sở mùa hè dưới 1 triệu",
  "Skincare cho da dầu mụn nhẹ",
  "Phụ kiện vintage phong cách Hàn Quốc",
];

/* ------------------------------------------------------------------ */
/* Seller Coach — 5-step audit + 4-week roadmap                     */
/* ------------------------------------------------------------------ */

export type AuditStep = {
  id: string;
  label: string;
  score: number; // 0..100
  tip: string;
};

export const SELLER_AUDIT: AuditStep[] = [
  { id: "listing",   label: "Listing Quality", score: 72, tip: "Mô tả ngắn, nên bổ sung 2-3 bullet về chất liệu + cách dùng." },
  { id: "pricing",   label: "Pricing",         score: 64, tip: "Đang cao hơn median category 8% — thử giảm 5-7% trong 7 ngày." },
  { id: "visuals",   label: "Visuals",         score: 58, tip: "Ảnh chính thiếu sáng, hero subject chỉ chiếm 32% frame." },
  { id: "reviews",   label: "Reviews",         score: 81, tip: "Reply rate 92%, nhưng phản hồi negative chậm (>24h)." },
  { id: "inventory", label: "Inventory",       score: 47, tip: "SKU top bán stockout 3 lần trong 30 ngày — set reorder buffer." },
];

export type RoadmapWeek = { week: number; title: string; bullets: string[] };

export const SELLER_ROADMAP: RoadmapWeek[] = [
  {
    week: 1,
    title: "Fix nền tảng",
    bullets: [
      "Reorder buffer cho 5 SKU top",
      "Reply 100% review negative trong 12h",
      "Đẩy 2 ảnh mới cho listing đèn sales",
    ],
  },
  {
    week: 2,
    title: "Tối ưu listing",
    bullets: [
      "Rewrite mô tả cho 10 listing theo AI gợi ý",
      "A/B test 3 hero images",
      "Bổ sung 5 video 15s cho top SKUs",
    ],
  },
  {
    week: 3,
    title: "Pricing & promotion",
    bullets: [
      "Điều chỉnh giá về median ± 5%",
      "Chạy voucher 10% trong 48h cho segment Loyalty",
      "Combo 3 sản phẩm bán chạy",
    ],
  },
  {
    week: 4,
    title: "Scale & retention",
    bullets: [
      "Ra mắt 2 SKU mới theo trend Q3",
      "Email win-back cho segment At Risk",
      "Review & lặp lại vòng audit",
    ],
  },
];

/* ------------------------------------------------------------------ */
/* Content Generator — 3 platform variants                          */
/* ------------------------------------------------------------------ */

export type ContentVariant = {
  platform: "Shopee" | "Tiki" | "TikTok Shop";
  title: string;
  body: string;
  predictedCtr: number; // 0..1
  rationale: string;
};

export const CONTENT_DEMO: ContentVariant[] = [
  {
    platform: "Shopee",
    title: "Áo khoác denim unisex — form rộng, wash nhẹ, mặc 4 mùa",
    body:
      "Denim 12oz wash nhẹ — không bai, không xù. Form rộng unisex, 2 size S–XL. Bỏ túi ngực + túi hông đủ laptop 14\". Free ship đơn từ 250k.",
    predictedCtr: 0.082,
    rationale: "Hero keywords: 'denim unisex', 'form rộng', '4 mùa'. Mention Free ship — tăng 18% CTR.",
  },
  {
    platform: "Tiki",
    title: "Áo khoác denim form rộng unisex | Local Brand X | Chính hãng",
    body:
      "Sản phẩm chính hãng Local Brand X. Chất liệu denim 12oz wash nhẹ, đường may gấp đôi. Đổi trả 7 ngày nếu lỗi. TikiNOW giao 2h tại TP.HCM & Hà Nội.",
    predictedCtr: 0.071,
    rationale: "Đề cao 'Chính hãng' + 'TikiNOW' — phù hợp khách Tiki tìm đảm bảo giao nhanh.",
  },
  {
    platform: "TikTok Shop",
    title: "DENIM JACKET siêu xinh — đi học đi chơi đều ổn 🥹",
    body:
      "Best seller tuần qua! Wash nhẹ mặc siêu mềm, form rộng giấu bụng. Đủ size S–XL. Comment 'DENIM' để nhận voucher 30k.",
    predictedCtr: 0.118,
    rationale: "Hook ngắn + emoji + comment-to-claim — pattern TikTok Shop thường thắng trên impulse.",
  },
];

/* ------------------------------------------------------------------ */
/* Recsys — Traditional CF vs AI reasoning                          */
/* ------------------------------------------------------------------ */

export type Recommendation = Product & { reason: string };

export const RECSYS_TRADITIONAL: Recommendation[] = PRODUCTS.slice(0, 4).map((p) => ({
  ...p,
  reason: "Collaborative filtering: người dùng tương tự (cosine 0.83) cũng đã mua.",
}));

export const RECSYS_AI: Recommendation[] = [
  { ...PRODUCTS[1], reason: "Bạn vừa mua serum BHA — C-vit là bước tiếp theo được chuyên gia khuyên." },
  { ...PRODUCTS[5], reason: "Da bạn da khô (signal từ quiz), Laneige mask lock ẩm 8h qua đêm." },
  { ...PRODUCTS[3], reason: "Son tint lì — match với 3 review gần đây của bạn đều khen 'lâu trôi, không khô'." },
  { ...PRODUCTS[2], reason: "Tote canvas phù hợp với style bạn lướt (canvas + earth-tone) trong 14 ngày qua." },
];
