"use client";

import { useEffect, useRef, useState } from "react";
import { Mic } from "lucide-react";
import { isVoiceInputSupported, listenOnce } from "@/lib/voice";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

/**
 * Push-to-talk mic button — the "Hey Cellaxnet" trigger. Renders nothing if
 * the browser has no SpeechRecognition support (e.g. Firefox desktop).
 *
 * `supported` starts `false` (matching SSR, where `window` doesn't exist) and
 * only flips after mount — checking `isVoiceInputSupported()` directly during
 * render would make the client's first paint differ from the server's,
 * triggering a React hydration mismatch.
 */
export function VoiceMicButton({
  onTranscript, disabled, className,
}: {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  const t = useT();
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    setSupported(isVoiceInputSupported());
  }, []);

  if (!supported) return null;

  function toggle() {
    if (listening) {
      stopRef.current?.();
      setListening(false);
      return;
    }
    setListening(true);
    stopRef.current = listenOnce({
      onResult: onTranscript,
      onEnd: () => setListening(false),
      onError: () => setListening(false),
    });
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={disabled}
      title='Nhấn để nói · "Hey Cellaxnet"'
      aria-label={listening ? "Đang nghe — nhấn để dừng" : t("Nhấn để nói bằng giọng nói")}
      aria-pressed={listening}
      className={cn(
        "inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border transition-colors",
        listening
          ? "animate-pulse border-danger/50 bg-danger/10 text-danger"
          : "border-border bg-bg-alt text-text-muted hover:border-accent hover:text-accent",
        className,
      )}
    >
      <Mic className="h-4 w-4" />
    </button>
  );
}
