import { Sparkles, User } from "lucide-react";
import { cn } from "@/lib/utils";

export type ChatRole = "user" | "assistant" | "system";

export function ChatBubble({
  role,
  content,
  timestamp,
  streaming,
}: {
  role: ChatRole;
  content: React.ReactNode;
  timestamp?: string;
  streaming?: boolean;
}) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "flex w-full gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md border",
          isUser
            ? "border-border bg-surface-2 text-text-muted"
            : "border-accent/30 bg-accent/10 text-accent",
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5" />
        ) : (
          <Sparkles className="h-3.5 w-3.5" />
        )}
      </div>

      <div className={cn("flex min-w-0 flex-col gap-1", isUser ? "items-end" : "items-start")}>
        <div className="flex items-center gap-2 text-2xs uppercase tracking-wider text-text-dim">
          <span>{role === "user" ? "bạn" : "trợ lý"}</span>
          {timestamp && <span className="mono normal-case tracking-normal">{timestamp}</span>}
          {streaming && (
            <span className="inline-flex items-center gap-1 text-accent">
              <span className="h-1 w-1 animate-pulse rounded-full bg-accent" />
              đang trả lời
            </span>
          )}
        </div>

        <div
          className={cn(
            "max-w-[640px] rounded-[10px] border px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "border-border bg-surface-2 text-text"
              : "border-accent/15 bg-surface text-text",
          )}
        >
          {content}
        </div>
      </div>
    </div>
  );
}

/**
 * Cursor that blinks while the LLM is still streaming tokens.
 * Pure CSS — no JS animation library required.
 */
export function Caret() {
  return (
    <span
      aria-hidden
      className="ml-0.5 inline-block h-3 w-[2px] translate-y-[2px] bg-accent align-middle"
      style={{ animation: "caret-blink 1.2s ease-in-out infinite" }}
    />
  );
}
