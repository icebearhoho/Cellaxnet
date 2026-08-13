/**
 * Feature API layer — connects the GenAI panels to the FastAPI backend
 * (endpoints under /api/v1). Every call maps the backend snake_case shapes to
 * the frontend camelCase types and falls back to the supplied mock data when the
 * backend is unreachable or NEXT_PUBLIC_DEMO_MODE=true — so the UI never breaks.
 */
import { api, ApiClientError } from "@/lib/api";
import type {
  Product,
  Recommendation,
  ContentVariant,
  AuditStep,
  RoadmapWeek,
} from "@/lib/mock-data";

const DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

// --- backend wire shapes -------------------------------------------------
type BackendProduct = {
  id: string; name: string; brand: string; category: string; platform: string;
  price_vnd: number; rating: number; reviews: number; similarity: number;
  image_hue?: number; image_url?: string | null;
};
type BackendRec = Omit<BackendProduct, "id" | "image_hue"> & { product_id: string; reason: string };
type BackendVariant = {
  platform: string; title: string; body: string; predicted_ctr: number; rationale: string;
};

function mapProduct(p: BackendProduct): Product {
  return {
    id: p.id, name: p.name, brand: p.brand,
    category: p.category as Product["category"],
    platform: p.platform as Product["platform"],
    priceVnd: p.price_vnd, rating: p.rating, reviews: p.reviews,
    similarity: p.similarity, imageHue: p.image_hue ?? 215,
    imageUrl: p.image_url ?? "", description: "",
  };
}

async function post<T>(path: string, body: unknown): Promise<T | null> {
  if (DEMO) return null;
  try {
    const env = await api.post<T>(path, body);
    return env.data as T;
  } catch {
    return null;
  }
}

async function get<T>(path: string): Promise<T | null> {
  if (DEMO) return null;
  try {
    const env = await api.get<T>(path);
    return env.data as T;
  } catch {
    return null;
  }
}

// --- #03 Personal Shopper -------------------------------------------------
export async function shopperProducts(
  query: string, topK: number, fallback: Product[],
): Promise<{ products: Product[]; live: boolean }> {
  const data = await get<{ products: BackendProduct[] }>(
    `/personal-shopper/products?query=${encodeURIComponent(query)}&top_k=${topK}`,
  );
  if (!data?.products?.length) return { products: fallback, live: false };
  return { products: data.products.map(mapProduct), live: true };
}

// --- #11 Recsys -----------------------------------------------------------
export async function recsysRecommend(
  signals: Record<string, string>, topK: number, fallback: Recommendation[],
): Promise<{ items: Recommendation[]; live: boolean; model?: string }> {
  const data = await post<{ items: BackendRec[]; model: string }>(
    "/recsys/", { signals, top_k: topK },
  );
  if (!data?.items?.length) return { items: fallback, live: false };
  const items = data.items.map((r) => ({
    ...mapProduct({ ...r, id: r.product_id }), reason: r.reason,
  }));
  return { items, live: true, model: data.model };
}

// --- #09 Content Generator ------------------------------------------------
export async function contentGenerate(
  productName: string, features: string, platforms: string[], fallback: ContentVariant[],
): Promise<{ variants: ContentVariant[]; live: boolean }> {
  const data = await post<{ variants: BackendVariant[] }>(
    "/content-generator/", { product_name: productName, features, platforms },
  );
  if (!data?.variants?.length) return { variants: fallback, live: false };
  const variants = data.variants.map((v) => ({
    platform: v.platform as ContentVariant["platform"],
    title: v.title, body: v.body, predictedCtr: v.predicted_ctr, rationale: v.rationale,
  }));
  return { variants, live: true };
}

// --- #01 Review Sentiment -------------------------------------------------
export type Sentiment = { sentiment: "positive" | "neutral" | "negative"; confidence: number; reason: string };

export async function analyzeSentiment(text: string, rating?: number): Promise<Sentiment | null> {
  return post<Sentiment>("/review-sentiment/", { text, rating: rating ?? null });
}

// --- #05 Fake Review ------------------------------------------------------
export type FakeVerdict = { is_fake: boolean; confidence: number; signals: string[]; reason: string };

export async function detectFake(text: string, rating?: number, category?: string): Promise<FakeVerdict | null> {
  return post<FakeVerdict>("/fake-review/", { text, rating: rating ?? null, category: category ?? null });
}

// --- #17 Seller Coach -----------------------------------------------------
export async function sellerCoach(
  fallback: { overall: number; audit: AuditStep[]; roadmap: RoadmapWeek[] },
): Promise<{ overall: number; audit: AuditStep[]; roadmap: RoadmapWeek[]; live: boolean }> {
  const data = await post<{ overall: number; audit: AuditStep[]; roadmap: RoadmapWeek[] }>(
    "/seller-coach/", {},
  );
  if (!data?.audit?.length) return { ...fallback, live: false };
  return { overall: data.overall, audit: data.audit, roadmap: data.roadmap, live: true };
}

// --- #19 Customer Segmentation ---------------------------------------------
export type SegmentationFeatures = {
  log_recency: number;
  seniority_months: number;
  log_followers: number;
  log_follows: number;
  log_products_liked: number;
  log_products_listed: number;
  log_products_sold: number;
  products_pass_rate: number;
  log_products_wished: number;
  log_products_bought: number;
  buy_ratio: number;
  wish_to_buy: number;
  has_any_app: number;
  has_profile_picture: number;
};

export type SegmentationResult = {
  persona: string;
  probabilities: Record<string, number>;
  model_version: string;
};

export async function predictSegmentation(
  features: SegmentationFeatures,
): Promise<SegmentationResult | null> {
  return post<SegmentationResult>("/segmentation/", features);
}

// --- #02 Dynamic Pricing ----------------------------------------------------
export type PricingResult = {
  recommended_price: number; low: number; high: number;
  category_median: number; sample_size: number; rationale: string;
};

export async function recommendPrice(
  productName: string, category: string, currentPrice?: number,
): Promise<PricingResult | null> {
  return post<PricingResult>("/dynamic-pricing/", {
    product_name: productName, category, current_price: currentPrice ?? null,
  });
}

// --- #04 Churn Prediction ---------------------------------------------------
export type ChurnResult = {
  churn_risk: number; risk_band: "low" | "medium" | "high";
  drivers: string[]; retention_action: string;
};

export async function scoreChurn(input: {
  recencyDays: number; frequencyOrders: number; sessionsLastMonth: number;
  cartAbandonRate: number; trend: "declining" | "stable" | "growing";
}): Promise<ChurnResult | null> {
  return post<ChurnResult>("/churn/", {
    recency_days: input.recencyDays, frequency_orders: input.frequencyOrders,
    sessions_last_month: input.sessionsLastMonth, cart_abandon_rate: input.cartAbandonRate,
    trend: input.trend,
  });
}

// --- Customer Journey Intelligence (Track 1, Đề 2 — bonus) ----------------
export type JourneyEventType = "search" | "click" | "view" | "review" | "cart" | "purchase" | "livestream";
export type JourneyEventInput = { type: JourneyEventType; category?: string; query?: string; ts?: number };
export type NextAction = "checkout" | "add_to_cart" | "compare" | "keep_browsing" | "leave";
export type FunnelStage = "awareness" | "consideration" | "intent" | "purchase";
export type JourneyResult = {
  will_purchase: boolean; purchase_probability: number;
  predicted_next_action: NextAction; next_action_label: string;
  funnel_stage: FunnelStage; engagement_score: number; nudge: string;
  top_category: string | null; category_breakdown: Record<string, number>;
  recommended_products: BackendProduct[]; reasoning: string;
  session_duration_seconds: number | null; avg_dwell_seconds: number | null;
  time_to_purchase_seconds: number | null; cart_abandoned: boolean | null;
};
export type JourneyResultMapped = Omit<JourneyResult, "recommended_products"> & { recommended_products: Product[] };

export async function analyzeJourney(events: JourneyEventInput[]): Promise<JourneyResultMapped | null> {
  const data = await post<JourneyResult>("/journey/", { events });
  if (!data) return null;
  return { ...data, recommended_products: data.recommended_products.map(mapProduct) };
}

/** Best-effort persistence of real tracked events (separate from analysis —
 * never blocks or fails the analyze flow). Returns the count persisted, or
 * null if unreachable/DEMO_MODE. */
export async function trackJourneyEvents(sessionId: string, events: JourneyEventInput[]): Promise<number | null> {
  const r = await post<{ persisted: number }>("/journey/events", { session_id: sessionId, events });
  return r?.persisted ?? null;
}

// Journey — auto-load real sessions (analysis is the raw JourneyResult shape)
export type JourneySession = {
  id: string; label: string;
  events: { type: string; category?: string; query?: string }[];
  video_url?: string | null;
  analysis: JourneyResult;
};
export type JourneySessions = { sessions: JourneySession[]; total: number };

export async function getJourneySessions(): Promise<JourneySessions | null> {
  return get<JourneySessions>("/journey/sessions");
}

// --- #10 Return/Refund Prediction ------------------------------------------
export type ReturnResult = { return_risk: number; risk_band: "low" | "medium" | "high"; drivers: string[]; action: string };

export async function scoreReturn(input: {
  category: string; priceVnd: number; isNewCustomer: boolean; sizeRelated: boolean;
  discountPct: number; reviewsRead: number;
}): Promise<ReturnResult | null> {
  return post<ReturnResult>("/return-prediction/", {
    category: input.category, price_vnd: input.priceVnd, is_new_customer: input.isNewCustomer,
    size_related: input.sizeRelated, discount_pct: input.discountPct, reviews_read: input.reviewsRead,
  });
}

// --- #15 Post-purchase Regret Predictor ------------------------------------
export type RegretResult = {
  regret_risk: number; risk_band: "low" | "medium" | "high"; drivers: string[]; reassurance_message: string;
};

export async function scoreRegret(input: {
  decisionTimeSeconds: number; revisitCount: number; purchaseHour: number; priceVnd: number; usedDiscount: boolean;
}): Promise<RegretResult | null> {
  return post<RegretResult>("/regret/", {
    decision_time_seconds: input.decisionTimeSeconds, revisit_count: input.revisitCount,
    purchase_hour: input.purchaseHour, price_vnd: input.priceVnd, used_discount: input.usedDiscount,
  });
}

// --- Customer Risk Intelligence — #04 Churn + #10 Return + #15 Regret combined
export type RiskBand = "low" | "medium" | "high" | null;
export type RiskRow = {
  id: string;
  customer: string;
  churn_risk: number | null;
  churn_band: RiskBand;
  return_risk: number | null;
  return_band: RiskBand;
  regret_risk: number | null;
  regret_band: RiskBand;
  high_risk_count: number;
};
export type RiskPortfolio = { customers: RiskRow[]; total: number; critical_count: number };

export async function getRiskPortfolio(): Promise<RiskPortfolio | null> {
  return get<RiskPortfolio>("/risk-portfolio/");
}

// --- #08 Sentiment-driven Inventory Alert ----------------------------------
export type InventoryAlertResult = {
  is_trending: boolean; trend_score: number; days_of_stock_left: number;
  alert_level: "none" | "watch" | "urgent"; recommended_restock_qty: number; reason: string;
};

export async function checkInventoryAlert(input: {
  productName: string; socialMentions7d: number; socialSentiment: number; currentStock: number; avgDailySales: number;
}): Promise<InventoryAlertResult | null> {
  return post<InventoryAlertResult>("/inventory-alert/", {
    product_name: input.productName, social_mentions_7d: input.socialMentions7d,
    social_sentiment: input.socialSentiment, current_stock: input.currentStock, avg_daily_sales: input.avgDailySales,
  });
}

// --- #16 Supply Chain Disruption Early Warning -----------------------------
export type DisruptionAlert = {
  title: string; region: string; severity: "low" | "medium" | "high";
  estimated_delay_days: number; contingency: string;
};
export type NewsArticle = { title: string; source: string; link: string; date: string; snippet: string };
export type SupplyChainResult = { alerts: DisruptionAlert[]; overall_risk: "low" | "medium" | "high"; summary: string; news: NewsArticle[]; news_live: boolean };

export async function checkSupplyChain(region: string, category: string): Promise<SupplyChainResult | null> {
  return post<SupplyChainResult>("/supply-chain/", { region, category });
}

// --- Shared category type (Thời trang / Mỹ phẩm / Phụ kiện) ----------------
export type Category = "Thời trang" | "Mỹ phẩm" | "Phụ kiện";

// --- Product Knowledge — vì sao doanh số thay đổi --------------------------
export type ProductKnowledgeResult = {
  sales_change_pct: number;
  direction: "up" | "down" | "flat";
  drivers: { factor: string; direction: "up" | "down"; impact: "low" | "medium" | "high" }[];
  promotion_effectiveness: string;
  explanation: string;
};

export async function analyzeProductKnowledge(input: {
  product: string;
  category: Category;
  sales_prev: number;
  sales_curr: number;
  price_change_pct?: number;
  promotion_active?: boolean;
  competitor_promo?: boolean;
  stock_status?: "ok" | "low" | "out";
  traffic_change_pct?: number;
}): Promise<ProductKnowledgeResult | null> {
  return post<ProductKnowledgeResult>("/product-knowledge/", input);
}

// --- Market Intelligence — phân tích đối thủ & giá -------------------------
export type MarketIntelligenceResult = {
  position: "cheaper" | "parity" | "pricier";
  recommended_action: "hold" | "match_price" | "undercut" | "differentiate";
  recommended_price_vnd: number;
  price_floor_vnd: number;
  margin_pct_at_recommended: number;
  competitor_effective_price_vnd: number;
  reasoning: string;
};

export async function analyzeMarketIntelligence(input: {
  our_product: string;
  category: Category;
  our_price_vnd: number;
  our_cost_vnd: number;
  competitor_name: string;
  competitor_price_vnd: number;
  competitor_discount_pct?: number;
  min_margin_pct?: number;
}): Promise<MarketIntelligenceResult | null> {
  return post<MarketIntelligenceResult>("/market-intelligence/", input);
}

// --- Creator Performance — hiệu quả KOL/KOC --------------------------------
export type CreatorItemInput = {
  creator: string;
  content_type: "video" | "livestream" | "post";
  views: number;
  engagements: number;
  attributed_sales_vnd: number;
};
export type CreatorPerformanceResult = {
  best_content_type: "video" | "livestream" | "post";
  recommended_creator: string;
  top_creators: {
    creator: string;
    content_type: string;
    total_sales_vnd: number;
    sales_per_1k_views: number;
    engagement_rate_pct: number;
  }[];
  insight: string;
};

export async function analyzeCreatorPerformance(input: {
  campaign_category: Category;
  items: CreatorItemInput[];
}): Promise<CreatorPerformanceResult | null> {
  return post<CreatorPerformanceResult>("/creator-performance/", input);
}

// --- Decision Intelligence — học từ quyết định quá khứ ----------------------
export type DecisionInput = {
  kind: "price" | "promo" | "ad" | "inventory";
  description: string;
  metric: "ROAS" | "sales_lift_pct" | "margin_pct" | "sell_through_pct";
  value: number;
  month?: number | null;
};
export type DecisionIntelligenceResult = {
  best_decision: { kind: string; description: string; metric: string; value: number };
  best_ad_month: number | null;
  recommended_action: string;
  reasoning: string;
};

export async function analyzeDecisionIntelligence(input: {
  situation: string;
  category: Category;
  decisions: DecisionInput[];
}): Promise<DecisionIntelligenceResult | null> {
  return post<DecisionIntelligenceResult>("/decision-intelligence/", input);
}

// --- AI Copilot — hỏi bất cứ điều gì, agent tự chọn công cụ ----------------
export type CopilotResult = {
  answer: string;
  skill_used: string;
  entity: string | null;
  impact_vnd: number | null;
  tool_result: Record<string, unknown>;
};

export async function askCopilot(question: string): Promise<CopilotResult | null> {
  return post<CopilotResult>("/copilot/ask", { question });
}

// --- AI Copilot Agent — multi-step, tự gọi nhiều công cụ --------------------
export type AgentStep = { tool: string; args: Record<string, unknown>; summary: string };
export type CopilotAgentResult = { answer: string; tools_used: string[]; steps: AgentStep[]; multi_step: boolean };

export async function askAgent(
  question: string,
  history: { role: "user" | "assistant"; content: string }[],
): Promise<CopilotAgentResult | null> {
  return post<CopilotAgentResult>("/copilot/agent", { question, history });
}

// --- Product Graph — quan hệ SKU/brand + sản phẩm tương tự (Đề 1) ----------
export type PGDriver = { factor: string; direction: "up" | "down"; impact: "low" | "medium" | "high" };
export type PGSimilar = { id: string; sku: string; name: string; brand: string; price_vnd: number; relation: string };
export type ProductGraphResult = {
  found: boolean;
  product: { id: string; sku: string; name: string; brand: string; category: string; price_vnd: number; cost_vnd: number; trend: string; stock_status: string } | null;
  sales: { sales_prev: number; sales_curr: number; change_pct: number; direction: "up" | "down" | "flat"; drivers: PGDriver[] } | null;
  similar_products: PGSimilar[];
  brand_siblings: string[];
  category_peers: number;
  promotions: { name: string; discount_pct: number; lift_pct: number; effectiveness: string }[];
  summary: string;
};

export async function exploreProductGraph(query: string): Promise<ProductGraphResult | null> {
  return post<ProductGraphResult>("/product-knowledge/graph", { query });
}

// --- Daily Briefing — hôm nay cần làm gì -----------------------------------
export type BriefingAction = {
  kind: "restock" | "reduce" | "reprice" | "investigate" | "promote";
  title: string;
  product: string;
  priority: "high" | "medium" | "low";
  impact_vnd: number;
  detail: string;
};
export type BriefingResult = {
  summary: string;
  total_impact_vnd: number;
  actions: BriefingAction[];
};

export async function getBriefing(): Promise<BriefingResult | null> {
  return get<BriefingResult>("/copilot/briefing");
}

// --- #13 Emotion-Aware Flash Sale Optimizer --------------------------------
export type FlashSaleResult = {
  hesitating: boolean; hesitation_score: number; trigger_now: boolean;
  suggested_discount_pct: number; message: string;
};

export async function analyzeHesitation(input: {
  dwellTimeSeconds: number; scrollDepthPct: number; revisitCount: number; cartOpenedNoPurchase: boolean; priceVnd: number;
}): Promise<FlashSaleResult | null> {
  return post<FlashSaleResult>("/flash-sale/", {
    dwell_time_seconds: input.dwellTimeSeconds, scroll_depth_pct: input.scrollDepthPct,
    revisit_count: input.revisitCount, cart_opened_no_purchase: input.cartOpenedNoPurchase, price_vnd: input.priceVnd,
  });
}

// --- Buyer storefront catalog ---------------------------------------------
export type StoreProduct = {
  id: string; sku: string; name: string; brand: string; category: string;
  price_vnd: number; rating: number; reviews: number; trend: string;
  image_url: string; image_urls: string[]; attributes: Record<string, string>;
};
export type StoreList = { products: StoreProduct[]; total: number };
export type StoreReview = { author: string; rating: number; text: string; days_ago: number };
export type StoreDetail = {
  product: StoreProduct | null; similar: StoreProduct[]; review_items: StoreReview[];
};

export async function getStoreProducts(q?: string, category?: string): Promise<StoreList | null> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  const qs = params.toString();
  return get<StoreList>(`/storefront/products${qs ? `?${qs}` : ""}`);
}

export async function getStoreProduct(id: string): Promise<StoreDetail | null> {
  return get<StoreDetail>(`/storefront/products/${encodeURIComponent(id)}`);
}

// --- Smart Restock Planner — chia vốn nhập hàng theo mùa vụ + sale big brand ---
export type ChannelId = "shopee" | "lazada" | "tiktok" | "own";
export type CaseId = "hot" | "slow" | "seasonal" | "dead";

export type ChannelMarketRow = {
  category: string; listings: number; share_pct: number;
  median_price_vnd: number; on_sale: number; avg_discount: number;
};
export type ChannelResult = {
  channel: ChannelId; name: string; kind: "marketplace" | "own";
  case: CaseId; case_label: string; case_desc: string;
  commission_pct: number;
  volume_factor: number; season_adj: number; trend_adj: number; demand_factor: number;
  expected_demand: number; order_qty: number; spend_vnd: number;
  expected_revenue_vnd: number; expected_profit_vnd: number;
  commission_cost_vnd: number; budget_share_pct: number; sku_count: number;
  verdict: string; measured: ChannelMarketRow[]; measurable: boolean;
  volume_from_orders: boolean;
};

export type RestockItem = {
  sku: string; name: string; brand: string; category: string;
  channel: ChannelId; channel_name: string;
  price_vnd: number; cost_vnd: number; stock: number; days_of_stock_left: number;
  season_index: number; competition_multiplier: number;
  baseline_demand: number; expected_demand: number;
  need_qty: number; order_qty: number; partial: boolean;
  spend_vnd: number; expected_revenue_vnd: number; expected_profit_vnd: number;
  unit_margin_vnd: number; roi: number; urgency: number; reason: string;
};
export type RestockSkipped = {
  sku: string; name: string; category: string; need_qty: number;
  cost_vnd: number; reason: string;
};
export type RestockOutlook = {
  category: string; season_index: number; season_index_prev: number;
  season_change_pct: number; momentum: number; direction: string;
  competition_multiplier: number; competition_level: string;
  combined_factor: number; outlook: "expand" | "hold" | "contract";
  advice: string; peak_month: number | null; low_month: number | null;
  monthly_index: number[];
};
export type RestockCompetition = {
  category: string; pressure: number; demand_multiplier: number;
  level: "low" | "medium" | "high"; note: string;
  brands_on_sale: number; brands_checked: number; avg_discount: number;
  leader_brand: string | null;
};
export type RestockBrand = {
  brand: string; category: string; offers_seen: number; offers_on_sale: number;
  sale_ratio: number; avg_discount: number; pressure: number;
};
export type RestockPlan = {
  month: number; horizon_days: number;
  budget_vnd: number; spent_vnd: number; remaining_vnd: number; budget_used_pct: number;
  item_count: number; skipped_count: number; total_units: number;
  expected_revenue_vnd: number; expected_profit_vnd: number;
  expected_margin_pct: number; roi_pct: number;
  items: RestockItem[]; skipped: RestockSkipped[];
  outlook: RestockOutlook[];
  channels: ChannelResult[]; channel_market_fetched_at: string | null;
  competition: RestockCompetition[]; brands: RestockBrand[];
  summary: string; data_source: string; trends_window: string | null;
  weeks_of_history: number; trends_fetched_at: string | null;
  brand_sale_fetched_at: string | null; live_refresh: boolean;
  scenario: boolean; competition_sensitivity: number;
};

/**
 * Why this one call reports its failures instead of collapsing to `null` like
 * the helpers above: the backend applies a global 30-req/min per-IP rate limit
 * (RateLimitMiddleware), and this panel is the one users click repeatedly while
 * tuning budget/month/horizon. Swallowing a 429 into `null` renders as "backend
 * unreachable", which sends people restarting a perfectly healthy stack. The
 * caller needs to tell "slow down" apart from "it's down" and "your input is
 * invalid".
 */
export type RestockFailure =
  | { kind: "rate_limited"; message: string; retryAfterS: number }
  | { kind: "validation"; message: string }
  | { kind: "offline"; message: string }
  | { kind: "demo"; message: string };

export type RestockResult =
  | { ok: true; plan: RestockPlan }
  | { ok: false; failure: RestockFailure };

export async function planRestock(input: {
  budget_vnd: number;
  month?: number;
  horizon_days?: number;
  categories?: Category[];
  scenario_pressure?: number | null;
  refresh_live?: boolean;
  channel_cases?: Partial<Record<ChannelId, CaseId>>;
  channel_fees?: Partial<Record<ChannelId, number>>;
}): Promise<RestockResult> {
  if (DEMO) {
    return {
      ok: false,
      failure: {
        kind: "demo",
        message:
          "Đang ở chế độ demo (NEXT_PUBLIC_DEMO_MODE=true) nên không gọi backend. Đặt lại thành false trong frontend/.env.local.",
      },
    };
  }
  try {
    const env = await api.post<RestockPlan>("/restock-planner/", input);
    return { ok: true, plan: env.data as RestockPlan };
  } catch (e) {
    if (e instanceof ApiClientError) {
      if (e.status === 429) {
        const details = e.envelope.error?.details as
          | { limit?: number }
          | undefined;
        return {
          ok: false,
          failure: {
            kind: "rate_limited",
            retryAfterS: 60,
            message: `Bấm quá nhanh — backend giới hạn ${details?.limit ?? 30} lượt/phút. Chờ khoảng 1 phút rồi bấm lại (backend vẫn chạy bình thường).`,
          },
        };
      }
      if (e.status === 422) {
        return {
          ok: false,
          failure: {
            kind: "validation",
            message: `Giá trị nhập không hợp lệ: ${e.envelope.error?.message ?? "kiểm tra lại vốn / số ngày phủ tồn kho"}.`,
          },
        };
      }
      return {
        ok: false,
        failure: {
          kind: "offline",
          message: `Backend trả lỗi ${e.status}: ${e.envelope.error?.message ?? e.message}`,
        },
      };
    }
    return {
      ok: false,
      failure: {
        kind: "offline",
        message:
          "Không kết nối được backend. Kiểm tra docker compose đã chạy và cổng 8000 mở.",
      },
    };
  }
}

// --- Kết nối KiotViet — một liên kết mang cả Shopee/Lazada/TikTok Shop ----
export type LinkStatus =
  | "not_configured" | "disconnected" | "pending" | "connected" | "error";

export type MarketplaceRow = {
  channel: string; name: string; orders: number;
  revenue_vnd: number; daily_orders: number;
};

export type ChannelLinkStatus = {
  platform: string;
  name: string;
  status: LinkStatus;
  configured: boolean;
  missing_settings: string[];
  retailer: string | null;
  connected_at: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  sync_days: number | null;
  total_orders: number | null;
  marketplaces: MarketplaceRow[];
  docs_url: string;
  portal_url: string;
  credentials_hint: string;
  supported: string[];
};

export async function getChannelLink(): Promise<ChannelLinkStatus | null> {
  return get<ChannelLinkStatus>("/channel-link/");
}

/**
 * Verifies the store's API keys against KiotViet. No redirect: KiotViet
 * authenticates server-to-server, so this either succeeds or returns the
 * reason it did not — usually wrong keys, which the caller should show
 * verbatim rather than flattening into "connection failed".
 */
export async function connectChannel(): Promise<
  { ok: true } | { ok: false; message: string }
> {
  try {
    await api.post("/channel-link/connect", {});
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiClientError) {
      return { ok: false, message: e.envelope.error?.message ?? e.message };
    }
    return { ok: false, message: "Không gọi được backend." };
  }
}

export type SyncResult = {
  days: number; total_orders: number; pages_read: number;
  first_order_at: string | null; last_order_at: string | null;
  marketplaces: MarketplaceRow[];
};

export async function syncChannel(): Promise<
  { ok: true; data: SyncResult } | { ok: false; message: string }
> {
  try {
    const env = await api.post<SyncResult>("/channel-link/sync", {});
    return { ok: true, data: env.data as SyncResult };
  } catch (e) {
    if (e instanceof ApiClientError) {
      return { ok: false, message: e.envelope.error?.message ?? e.message };
    }
    return { ok: false, message: "Không gọi được backend." };
  }
}

export async function disconnectChannel(): Promise<boolean> {
  return (await post<{ removed: boolean }>("/channel-link/disconnect", {})) !== null;
}

// --- Marketplace connect: seller accounts + per-platform shop links --------
// Direct OAuth to Shopee / Lazada / TikTok Shop. Separate from the KiotViet
// aggregator link above: one seller account here owns many shops, each shop
// authorised against its own marketplace with its own credentials.

export type MarketplaceId = "shopee" | "lazada" | "tiktok";
export type ShopStatus =
  | "pending" | "connected" | "expired" | "revoked" | "error" | "disconnected";

export type MarketplacePlatform = {
  platform: MarketplaceId;
  display_name: string;
  configured: boolean;
  missing_settings: string[];
  console_url: string;
  /** Built vs merely planned — the UI must not present these the same way. */
  implemented: boolean;
};

export type SellerAccount = {
  id: number;
  name: string;
  business_type: string;
  contact_email: string | null;
  contact_phone: string | null;
  status: string;
  shop_count: number;
  created_at: string | null;
};

export type ShopConnection = {
  id: number;
  seller_account_id: number;
  platform: MarketplaceId;
  platform_label: string;
  external_shop_id: string;
  shop_name: string | null;
  region: string;
  status: ShopStatus;
  status_label: string;
  authorized_at: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  products: number;
  orders: number;
};

export async function getMarketplacePlatforms(): Promise<MarketplacePlatform[] | null> {
  return get<MarketplacePlatform[]>("/marketplace/platforms");
}

export async function getSellerAccounts(): Promise<SellerAccount[] | null> {
  return get<SellerAccount[]>("/marketplace/accounts");
}

export async function createSellerAccount(input: {
  name: string; business_type?: string;
  contact_email?: string | null; contact_phone?: string | null;
}): Promise<SellerAccount | null> {
  return post<SellerAccount>("/marketplace/accounts", input);
}

export async function getShopConnections(
  sellerAccountId?: number,
): Promise<ShopConnection[] | null> {
  const qs = sellerAccountId ? `?seller_account_id=${sellerAccountId}` : "";
  return get<ShopConnection[]>(`/marketplace/shops${qs}`);
}

/**
 * Starts authorisation. Reports its refusal rather than collapsing to `null`:
 * the usual reason is that the marketplace's app credentials are not configured
 * yet, and the seller needs to be told which ones — "something went wrong"
 * sends them looking at their own account instead.
 */
export async function beginShopConnect(
  sellerAccountId: number, platform: MarketplaceId,
): Promise<{ ok: true; authorizeUrl: string } | { ok: false; message: string }> {
  try {
    const env = await api.post<{ authorize_url: string }>("/marketplace/connect", {
      seller_account_id: sellerAccountId, platform,
    });
    return { ok: true, authorizeUrl: (env.data as { authorize_url: string }).authorize_url };
  } catch (e) {
    if (e instanceof ApiClientError) {
      return { ok: false, message: e.envelope.error?.message ?? e.message };
    }
    return { ok: false, message: "Không gọi được backend." };
  }
}

export type ShopSyncResult = {
  shop_connection_id: number; products: number; orders: number; errors: string[];
};

export async function syncShop(
  shopId: number,
): Promise<{ ok: true; data: ShopSyncResult } | { ok: false; message: string }> {
  try {
    const env = await api.post<ShopSyncResult>(`/marketplace/shops/${shopId}/sync`, {});
    return { ok: true, data: env.data as ShopSyncResult };
  } catch (e) {
    if (e instanceof ApiClientError) {
      return { ok: false, message: e.envelope.error?.message ?? e.message };
    }
    return { ok: false, message: "Không gọi được backend." };
  }
}

export async function disconnectShop(shopId: number): Promise<boolean> {
  return (await post<{ disconnected: boolean }>(
    `/marketplace/shops/${shopId}/disconnect`, {}
  )) !== null;
}

// --- Real review submission + moderation queue -----------------------------
export type ReviewSubmitStatus = "published" | "pending" | "flagged" | "rejected";
export type ReviewSubmitResult = { status: ReviewSubmitStatus; message: string; review: StoreReview | null };

export async function submitStoreReview(
  id: string, authorName: string, rating: number, text: string,
): Promise<ReviewSubmitResult | null> {
  return post<ReviewSubmitResult>(`/storefront/products/${encodeURIComponent(id)}/reviews`, {
    author_name: authorName, rating, text,
  });
}

export type ReviewQueueItem = {
  id: number; product_id: string; product_name: string; author_name: string;
  rating: number; text: string; status: ReviewSubmitStatus;
  moderation_reason: string | null; moderation_confidence: number | null; created_at: string;
};

export async function getReviewQueue(): Promise<ReviewQueueItem[] | null> {
  return get<ReviewQueueItem[]>("/storefront/reviews/queue");
}

export async function approveReview(id: number): Promise<{ id: number; status: string } | null> {
  return post(`/storefront/reviews/${id}/approve`, {});
}

export async function rejectReview(id: number): Promise<{ id: number; status: string } | null> {
  return post(`/storefront/reviews/${id}/reject`, {});
}
