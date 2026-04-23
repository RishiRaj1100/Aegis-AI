import { useCallback, useEffect, useRef, useState } from "react";
import type { Language } from "@/types/aegis";
import { submitVoice } from "@/lib/aegisApi";

// Browser SpeechRecognition typing shim
type AnyWindow = Window & { SpeechRecognition?: any; webkitSpeechRecognition?: any };

export function useVoiceInput(language: Language) {
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [detectedLanguage, setDetectedLanguage] = useState<Language>(language);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stop = useCallback(() => {
    setRecording(false);
    try {
      recognitionRef.current?.stop?.();
    } catch {}
    try {
      mediaRef.current?.stop?.();
    } catch {}
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setTranscript("");

    const w = window as AnyWindow;
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;

    // Prefer in-browser recognition for instant feedback
    if (SR) {
      const r = new SR();
      r.lang = language === "hi" ? "hi-IN" : "en-US";
      r.interimResults = true;
      r.continuous = false;
      r.onresult = (e: any) => {
        let text = "";
        for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
        setTranscript(text.trim());
      };
      r.onerror = (e: any) => setError(e?.error ?? "voice_error");
      r.onend = () => setRecording(false);
      recognitionRef.current = r;
      try {
        r.start();
        setRecording(true);
        setDetectedLanguage(language);
        return;
      } catch (e: any) {
        setError(e?.message ?? "voice_start_failed");
      }
    }

    // Fallback: record + send to backend
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          const res = await submitVoice(blob, language);
          setTranscript(res.transcript);
          setDetectedLanguage(res.detected_language);
        } catch (e: any) {
          setError(e?.message ?? "voice_upload_failed");
        }
      };
      mediaRef.current = mr;
      mr.start();
      setRecording(true);
    } catch (e: any) {
      setError(e?.message ?? "mic_permission_denied");
    }
  }, [language]);

  useEffect(() => () => stop(), [stop]);

  return { recording, transcript, detectedLanguage, error, start, stop, setTranscript };
}
