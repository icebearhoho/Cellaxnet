"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ChatBubble, Caret } from "@/components/genai/chat-bubble";
import { PromptChips } from "@/components/genai/prompt-chips";
import { ProductCard } from "@/components/genai/product-card";
import { VoiceMicButton } from "@/components/genai/voice-mic-button";
import {
  PRODUCTS,
  SHOPPER_CHIPS,
  type Product,
} from "@/lib/mock-data";
import { shopperProducts } from "@/lib/features";
import { trackEvent, guessCategory } from "@/lib/journey-track";
import { speak } from "@/lib/voice";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

type Turn = {
  id: string;
  role: "user" | "assistant";
  text: string;
  products?: Product[];
  /** When true the assistant is still streaming this turn. */
  streaming?: boolean;
  createdAt: string;
};

const INITIAL_GREETING: Turn = {
  id: "t0",
  role: "assistant",
  text:
    "Chào bạn! Mình có thể gợi ý quà, son, đồ đi làm hoặc sản phẩm chăm sóc da theo phong cách và ngân sách của bạn. Hôm nay bạn đang tìm gì?",
  products: [],
  createdAt: "now",
};

function pickProducts(query: string): Product[] {
  const q = query.toLowerCase();
  const scored = PRODUCTS.map((p) => {
    const text = `${p.name} ${p.brand} ${p.category} ${p.description}`.toLowerCase();
    let s = 0;
    if (q.includes("quà") || q.includes("sinh nhật")) s += p.category === "Phụ kiện" ? 2 : 0;
    if (q.includes("son") || q.includes("môi")) s += p.category === "Mỹ phẩm" && p.name.toLowerCase().includes("son") ? 3 : 0;
    if (q.includes("skincare") || q.includes("da")) s += p.category === "Mỹ phẩm" ? 2 : 0;
    if (q.includes("công sở") || q.includes("làm")) s += p.category === "Thời trang" ? 2 : 0;
    if (q.includes("đi chơi") || q.includes("học")) s += p.category === "Thời trang" ? 1 : 0;
    if (text.includes(q.split(/\s+/)[0] ?? "")) s += 1;
    return { p, s };
  })
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 8)
    .map((x) => x.p);

  return scored.length ? scored : PRODUCTS.slice(0, 8);
}

function makeAssistantReply(query: string, picks: Product[]): string {
  const intro = `Dựa trên câu hỏi "${query}", mình gợi ý ${picks.length} sản phẩm phù hợp nhất từ catalog Shopee · Tiki · TikTok Shop.`;
  const lines = picks
    .map((p, i) => `${i + 1}. ${p.name} — ${p.brand} (${p.platform}, ${p.rating.toFixed(1)}★)`)
    .join("\n");
  return `${intro}\n\n${lines}\n\nBạn muốn mình đi sâu hơn vào tiêu chí nào (giá, brand, rating, platform)?`;
}

export function PersonalShopperPanel() {
  const t = useT();
  const [turns, setTurns] = useState<Turn[]>([INITIAL_GREETING]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [turns.length, pending]);

  async function send(query: string, viaVoice = false) {
    if (!query.trim() || pending) return;

    // Record the shopper's real search behaviour for Journey analysis.
    trackEvent("search", { category: guessCategory(query), query: query.trim() });

    const userTurn: Turn = {
      id: `u${Date.now()}`,
      role: "user",
      text: query,
      createdAt: new Date().toISOString().slice(11, 16),
    };
    setTurns((prev) => [...prev, userTurn]);
    setDraft("");
    setPending(true);
    setError(false);

    // Retrieve products from the backend (falls back to local mock ranking).
    let picks: Product[];
    try {
      const res = await shopperProducts(query, 8, pickProducts(query));
      picks = res.products;
    } catch {
      setError(true);
      setPending(false);
      return;
    }
    const reply = makeAssistantReply(query, picks);

    const assistantTurn: Turn = {
      id: `a${Date.now()}`,
      role: "assistant",
      text: reply,
      products: picks,
      streaming: true,
      createdAt: new Date().toISOString().slice(11, 16),
    };
    setTurns((prev) => [...prev, assistantTurn]);
    if (viaVoice) speak(reply);

    // Stop the caret after the full reply is "streamed".
    const total = reply.length * 18;
    window.setTimeout(() => {
      setTurns((prev) =>
        prev.map((t) => (t.id === assistantTurn.id ? { ...t, streaming: false } : t)),
      );
      setPending(false);
    }, Math.min(total, 6000));
  }

  const hasMessages = turns.length > 1;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      {/* Chat thread */}
      <div className="lg:col-span-8">
        <div className="flex h-[640px] flex-col rounded-lg border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="live-dot" />
              <span className="text-xs font-medium text-text-dim">
                {t("Trợ lý mua sắm · sẵn sàng")}
              </span>
            </div>
            <div className="flex items-center gap-2 text-2xs text-text-muted">
              <Badge variant="muted">Catalog demo</Badge>
            </div>
          </div>

          <div ref={listRef} className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
            {turns.map((t) => (
              <div key={t.id} className="space-y-3">
                <ChatBubble
                  role={t.role}
                  timestamp={t.createdAt}
                  streaming={t.streaming}
                  content={
                    t.streaming ? (
                      <span className="whitespace-pre-wrap">
                        {t.text.slice(0, Math.max(0, Math.floor((turns.length) * 0)))}
                        {/* text is rendered fully below; caret indicates streaming */}
                        <StreamingReplyText text={t.text} tick={pending} />
                      </span>
                    ) : (
                      <span className="whitespace-pre-wrap">{t.text}</span>
                    )
                  }
                />

                {t.products && t.products.length > 0 && !t.streaming && (
                  <div className="ml-10 grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {t.products.map((p) => (
                      <ProductCard
                        key={p.id}
                        product={p}
                        similarity={p.similarity}
                        onInteract={(kind) =>
                          trackEvent(kind, { category: p.category })
                        }
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
            {error && (
              <p className="text-sm text-danger">{t("Không lấy được gợi ý. Kiểm tra kết nối backend rồi thử lại.")}</p>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-border p-3">
            {!hasMessages && (
              <div className="mb-3">
                <PromptChips items={SHOPPER_CHIPS} onSelect={(v) => send(v)} />
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send(draft);
              }}
              className="flex items-center gap-2"
            >
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder='Hỏi gì đó — ví dụ: son cho da ngăm dưới 350k… hoặc bấm mic và nói "Hey Cellaxnet"'
                disabled={pending}
                className="h-10"
              />
              <VoiceMicButton disabled={pending} onTranscript={(t) => send(t, true)} />
              <Button type="submit" size="lg" disabled={pending || !draft.trim()}>
                <Send className="h-3.5 w-3.5" />
                {t("Gửi")}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Sidebar — context + chips */}
      <aside className="lg:col-span-4 space-y-4">
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-xs font-medium text-text-dim">
            {t("Nguồn gợi ý")}
          </div>
          <div className="mt-3 space-y-2 text-sm">
            <Row k={t("Danh mục")} v={t("Thời trang, mỹ phẩm, phụ kiện")} />
            <Row k={t("Sàn tham khảo")} v="Shopee · Tiki · TikTok Shop" />
            <Row k="Ưu tiên" v={t("Nhu cầu, ngân sách và đánh giá")} />
            <Row k={t("Cập nhật")} v={t("Dữ liệu mẫu gần đây")} />
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-xs font-medium text-text-dim">
            {t("Gợi ý nhanh")}
          </div>
          <div className="mt-3">
            <PromptChips items={SHOPPER_CHIPS} onSelect={(v) => send(v)} />
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-4 text-xs text-text-muted">
          <span className="text-xs font-medium text-text-dim">
            {t("Lưu ý")}
          </span>
          <p className="mt-2">
            {t("Gợi ý được tạo từ danh mục mẫu. Hãy kiểm tra giá và thông tin trên trang sản phẩm trước khi mua.")}
          </p>
        </div>
      </aside>
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-text-muted">{k}</span>
      <span className={cn("truncate text-right", mono ? "mono text-text" : "text-text")}>
        {v}
      </span>
    </div>
  );
}

/**
 * Demo-mode "streaming" — reveal text progressively to mimic SSE.
 * Replaced by real `EventSource` once the backend is live.
 */
function StreamingReplyText({ text, tick }: { text: string; tick: boolean }) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    setShown("");
    if (!tick) return;
    let i = 0;
    const id = window.setInterval(() => {
      i = Math.min(text.length, i + 4);
      setShown(text.slice(0, i));
      if (i >= text.length) window.clearInterval(id);
    }, 16);
    return () => window.clearInterval(id);
  }, [text, tick]);

  if (!tick) return <>{text}</>;
  return (
    <>
      {shown}
      <Caret />
    </>
  );
}
