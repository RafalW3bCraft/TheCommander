/** Browser speech helpers. No server voice pipeline; no paid STT/TTS calls. */

export type SpeechCapability = {
  stt: boolean;
  tts: boolean;
  sttReason: string;
  ttsReason: string;
};

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionResultEventLike = {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0: { transcript: string };
  }>;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

function recognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function detectSpeechCapability(): SpeechCapability {
  const stt = Boolean(recognitionConstructor());
  const tts =
    typeof window !== "undefined" &&
    typeof window.speechSynthesis !== "undefined" &&
    typeof SpeechSynthesisUtterance !== "undefined";
  return {
    stt,
    tts,
    sttReason: stt
      ? ""
      : "Dictation needs a browser that supports the Web Speech API (for example Chrome or Edge). No server speech service is configured.",
    ttsReason: tts
      ? ""
      : "Voice playback unavailable in this browser. No text-to-speech service is configured on the server.",
  };
}

export function createRecognition(): SpeechRecognitionLike | null {
  const Ctor = recognitionConstructor();
  if (!Ctor) return null;
  const recognition = new Ctor();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  return recognition;
}

export function speakText(
  text: string,
): { ok: true } | { ok: false; reason: string } {
  const capability = detectSpeechCapability();
  if (!capability.tts) return { ok: false, reason: capability.ttsReason };
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) return { ok: false, reason: "Nothing to read aloud." };
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleaned.slice(0, 4000));
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
  return { ok: true };
}

export function stopSpeaking(): void {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

export function humanConnectionStatus(status: string): string {
  switch (status) {
    case "unconfigured":
      return "Not set up yet";
    case "configured":
      return "Saved — test to confirm";
    case "validated":
      return "Ready";
    case "stale":
      return "Needs a fresh check";
    case "expired":
      return "Credential expired";
    case "revoked":
      return "Removed";
    case "disabled":
      return "Turned off";
    case "invalid":
      return "Could not verify";
    default:
      return status.replaceAll("_", " ");
  }
}
