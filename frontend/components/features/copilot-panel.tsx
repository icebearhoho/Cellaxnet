"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Send, Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VoiceMicButton } from "@/components/genai/voice-mic-button";
import { askAgent, type CopilotAgentResult } from "@/lib/features";
import { speak } from "@/lib/voice";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; result: CopilotAgentResult };

const EXAMPLES = [
  "Vì sao doanh số váy hoa nhí midi giảm và nên chỉnh giá thế nào?",
  "Nên hợp tác KOL nào cho mỹ phẩm và khi nào đẩy ads?",
  "Hôm nay tôi nên ưu tiên làm gì?",
  "Sản phẩm nào tương tự serum vitamin c?",
];

export function CopilotPanel() {
  const t = useT();
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, busy]);

  async function send(question: string, viaVoice = false) {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(false);
    setDraft("");

    const history = messages.map((m) => ({
      role: m.role,
      content: m.role === "user" ? m.text : m.result.answer,
    }));

    setMessages((prev) => [...prev, { id: `u${Date.now()}`, role: "user", text: q }]);

    const r = await askAgent(q, history);
    setError(r === null);
    if (r) {
      setMessages((prev) => [...prev, { id: `a${Date.now()}`, role: "assistant", result: r }]);
      if (viaVoice) speak(r.answer);
    }
    setBusy(false);
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <div className="lg:col-span-8">
        <div className="flex h-[640px] flex-col rounded-lg border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="live-dot" />
              <span className="text-xs font-medium text-text-dim">
                {t("Trợ lý vận hành · sẵn sàng")}
              </span>
            </div>
          </div>

          <div ref={listRef} className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
            {!hasMessages && (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <Bot className="h-9 w-9 text-accent" />
                <p className="mt-3 text-sm font-medium text-text">{t("Hỏi bất cứ điều gì về shop của bạn")}</p>
                <p className="mt-1 max-w-sm text-xs text-text-muted">
                  {t("Hỏi về doanh số, giá đối thủ, nhà sáng tạo hoặc tồn kho để nhận một câu trả lời tổng hợp.")}
                </p>
              </div>
            )}

            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="flex items-start justify-end gap-2.5">
                  <div className="max-w-[80%] rounded-lg rounded-tr-sm bg-accent/15 px-3.5 py-2.5 text-sm text-text">
                    {m.text}
                  </div>
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-bg-alt text-text-muted">
                    <User className="h-3.5 w-3.5" />
                  </span>
                </div>
              ) : (
                <div key={m.id} className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent/40 bg-accent/10 text-accent">
                    <Bot className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0 max-w-[85%] space-y-2.5">
                    <div className="rounded-lg rounded-tl-sm border border-border bg-bg-alt px-3.5 py-2.5">
                      <div className="markdown-response text-sm leading-relaxed text-text">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.result.answer}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </div>
              ),
            )}

            {busy && (
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Đang tổng hợp dữ liệu… (có thể mất 5–15 giây)
              </div>
            )}
            {error && (
              <p className="text-sm text-danger">{t("Không lấy được câu trả lời. Kiểm tra kết nối backend rồi thử lại.")}</p>
            )}
          </div>

          <div className="border-t border-border p-3">
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
                placeholder='Ví dụ: vì sao doanh số giảm tuần này? · hoặc bấm mic và nói "Hey Cellaxnet"'
                disabled={busy}
                className="h-10"
              />
              <VoiceMicButton disabled={busy} onTranscript={(t) => send(t, true)} />
              <Button type="submit" size="lg" disabled={busy || !draft.trim()}>
                {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Gửi
              </Button>
            </form>
          </div>
        </div>
      </div>

      <aside className="lg:col-span-4 space-y-4">
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-xs font-medium text-text-dim">{t("Câu hỏi mẫu")}</div>
          <div className="mt-3 flex flex-col gap-2">
            {EXAMPLES.map((q) => (
              <button
                key={q}
                type="button"
                disabled={busy}
                onClick={() => send(q)}
                className={cn(
                  "rounded-md border border-border bg-bg-alt px-3 py-2 text-left text-xs text-text-muted transition-colors",
                  "hover:border-accent hover:text-text disabled:opacity-50",
                )}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-4 text-xs text-text-muted">
          <span className="text-xs font-medium text-text-dim">{t("Cách hoạt động")}</span>
          <p className="mt-2">
            {t("Trợ lý kết hợp dữ liệu giá, doanh số, nhà sáng tạo và tồn kho để đưa ra câu trả lời ngắn gọn cùng việc nên làm tiếp theo. Có thể hỏi bằng giọng nói — bấm mic và nói.")}
          </p>
        </div>
      </aside>
    </div>
  );
}
