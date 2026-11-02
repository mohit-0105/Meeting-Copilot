"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface UseSpeechRecognitionProps {
  onTranscript?: (text: string) => void;
  lang?: string;
}

export function useSpeechRecognition({
  onTranscript,
  lang = "en-US",
}: UseSpeechRecognitionProps = {}) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimText, setInterimText] = useState("");
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;

      if (SpeechRecognition) {
        setIsSupported(true);
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = lang;

        recognition.onresult = (event: any) => {
          let currentInterim = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcriptChunk = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              const cleaned = transcriptChunk.trim();
              if (cleaned) {
                setTranscript(cleaned);
                if (onTranscript) {
                  onTranscript(cleaned);
                }
              }
              setInterimText("");
            } else {
              currentInterim += transcriptChunk;
            }
          }
          if (currentInterim) {
            setInterimText(currentInterim);
          }
        };

        recognition.onerror = (event: any) => {
          if (event.error !== "no-speech") {
            setError(event.error);
          }
        };

        recognition.onend = () => {
          // If intentionally listening, restart on brief pauses
          if (recognitionRef.current?.shouldListen) {
            try {
              recognition.start();
            } catch {
              // already active
            }
          } else {
            setIsListening(false);
          }
        };

        recognitionRef.current = recognition;
      } else {
        setIsSupported(false);
        setError("Browser speech recognition not supported in this browser. Please use Chrome or Edge.");
      }
    }
  }, [lang, onTranscript]);

  const startListening = useCallback(() => {
    setError(null);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.shouldListen = true;
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err: any) {
        console.warn("Speech recognition already running:", err);
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.shouldListen = false;
      recognitionRef.current.stop();
      setIsListening(false);
      setInterimText("");
    }
  }, []);

  return {
    isListening,
    isSupported,
    transcript,
    interimText,
    error,
    startListening,
    stopListening,
  };
}
