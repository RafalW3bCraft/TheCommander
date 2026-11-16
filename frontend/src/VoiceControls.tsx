import { useEffect, useRef, useState } from "react";
import {
  createRecognition,
  detectSpeechCapability,
  speakText,
  stopSpeaking,
  type SpeechCapability,
} from "./voice";

export function useSpeechCapability(): SpeechCapability {
  const [capability, setCapability] = useState<SpeechCapability>(() =>
    detectSpeechCapability(),
  );
  useEffect(() => {
    setCapability(detectSpeechCapability());
  }, []);
  return capability;
}

export function DictationButton({
  disabled,
  onTranscript,
  onListeningChange,
}: {
  disabled?: boolean;
  onTranscript: (text: string, final: boolean) => void;
  onListeningChange?: (listening: boolean) => void;
}) {
  const capability = useSpeechCapability();
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const recognitionRef = useRef<ReturnType<typeof createRecognition>>(null);
  const onTranscriptRef = useRef(onTranscript);
  const onListeningChangeRef = useRef(onListeningChange);
  onTranscriptRef.current = onTranscript;
  onListeningChangeRef.current = onListeningChange;

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  function setListeningState(next: boolean) {
    setListening(next);
    onListeningChangeRef.current?.(next);
  }

  function stop() {
    recognitionRef.current?.stop();
    setListeningState(false);
  }

  function start() {
    setError("");
    const recognition = createRecognition();
    if (!recognition) {
      setError(capability.sttReason);
      return;
    }
    recognitionRef.current = recognition;
    recognition.onresult = (event) => {
      let finalText = "";
      let interim = "";
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) finalText += result[0].transcript;
        else interim += result[0].transcript;
      }
      const combined = (finalText + " " + interim).replace(/\s+/g, " ").trim();
      if (combined) onTranscriptRef.current(combined, interim.length === 0);
    };
    recognition.onerror = (event) => {
      setListeningState(false);
      if (
        event.error === "not-allowed" ||
        event.error === "service-not-allowed"
      ) {
        setError(
          "Microphone permission was denied. Allow the mic for this site, or type your message.",
        );
      } else if (event.error === "no-speech") {
        setError("No speech heard. Try again, or type your message.");
      } else if (event.error !== "aborted") {
        setError(
          "Dictation stopped (" + event.error + "). You can still type.",
        );
      }
    };
    recognition.onend = () => {
      setListeningState(false);
    };
    try {
      recognition.start();
      setListeningState(true);
    } catch {
      setError(
        "Could not start the microphone. Try again, or type your message.",
      );
      setListeningState(false);
    }
  }

  return (
    <div className="voice-controls">
      <button
        type="button"
        className={listening ? "" : "secondary"}
        aria-label={listening ? "Stop dictation" : "Start dictation"}
        aria-pressed={listening}
        aria-describedby="dictation-help"
        disabled={disabled || !capability.stt}
        title={
          capability.stt
            ? listening
              ? "Stop dictation"
              : "Speak your message into the prompt"
            : capability.sttReason
        }
        onClick={() => (listening ? stop() : start())}
      >
        {listening ? "Listening… stop" : "Dictate"}
      </button>
      <small id="dictation-help" role="status">
        {error
          ? error
          : !capability.stt
            ? capability.sttReason
            : listening
              ? "Listening. Click stop when you finish speaking. Text goes into the prompt; it does not unlock tools."
              : "Optional: dictate into the prompt with your browser microphone. No paid speech service is used."}
      </small>
    </div>
  );
}

export function SpeakReplyButton({ text }: { text: string }) {
  const capability = useSpeechCapability();
  const [error, setError] = useState("");
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    return () => stopSpeaking();
  }, []);

  if (!capability.tts) {
    return (
      <small className="voice-playback-unavailable" role="status">
        Voice playback unavailable
      </small>
    );
  }

  return (
    <div className="voice-playback">
      <button
        type="button"
        className="quiet"
        aria-label={speaking ? "Stop reading aloud" : "Read reply aloud"}
        onClick={() => {
          if (speaking) {
            stopSpeaking();
            setSpeaking(false);
            return;
          }
          const result = speakText(text);
          if (!result.ok) {
            setError(result.reason);
            setSpeaking(false);
            return;
          }
          setError("");
          setSpeaking(true);
          const watch = window.setInterval(() => {
            if (!window.speechSynthesis.speaking) {
              window.clearInterval(watch);
              setSpeaking(false);
            }
          }, 400);
        }}
      >
        {speaking ? "Stop reading" : "Read aloud"}
      </button>
      {error && (
        <small role="status" className="voice-playback-unavailable">
          {error}
        </small>
      )}
    </div>
  );
}
