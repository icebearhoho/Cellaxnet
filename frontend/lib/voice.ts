"use client";
/**
 * Browser-native voice I/O (Web Speech API) — no backend involved. Speech
 * recognition (STT) fills the existing chat input; speech synthesis (TTS)
 * reads the assistant's reply aloud. Push-to-talk, not a real always-on
 * wake-word — the mic button is the "Hey Cellaxnet" trigger.
 */

type SpeechRecognitionResultLike = { transcript: string };
type SpeechRecognitionEventLike = { results: SpeechRecognitionResultLike[][] };
type SpeechRecognitionErrorEventLike = { error: string };

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
};

function getRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition) as (new () => SpeechRecognitionLike) | null;
}

export function isVoiceInputSupported(): boolean {
  return getRecognitionCtor() !== null;
}

export function isVoiceOutputSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** Starts one speech-recognition turn. Returns a stop function, or null if unsupported. */
export function listenOnce(opts: {
  lang?: string;
  onResult: (transcript: string) => void;
  onEnd?: () => void;
  onError?: (message: string) => void;
}): (() => void) | null {
  const Ctor = getRecognitionCtor();
  if (!Ctor) return null;
  const rec = new Ctor();
  rec.lang = opts.lang ?? "vi-VN";
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.onresult = (e) => {
    const transcript = e.results?.[0]?.[0]?.transcript ?? "";
    if (transcript) opts.onResult(transcript);
  };
  rec.onerror = (e) => opts.onError?.(e.error ?? "unknown");
  rec.onend = () => opts.onEnd?.();
  rec.start();
  return () => rec.stop();
}

export function speak(text: string, lang = "vi-VN"): void {
  if (!isVoiceOutputSupported() || !text.trim()) return;
  window.speechSynthesis.cancel(); // don't stack up replies
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang;
  window.speechSynthesis.speak(utter);
}

export function stopSpeaking(): void {
  if (isVoiceOutputSupported()) window.speechSynthesis.cancel();
}
