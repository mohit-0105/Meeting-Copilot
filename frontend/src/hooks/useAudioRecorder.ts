"use client";

import { useState, useRef, useCallback } from "react";

interface UseAudioRecorderProps {
  onChunkAvailable?: (base64Data: string, format: string) => void;
  timeslice?: number; // Milliseconds between chunks (default: 3000ms)
}

export function useAudioRecorder({
  onChunkAvailable,
  timeslice = 3000,
}: UseAudioRecorderProps = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event: BlobEvent) => {
        if (event.data && event.data.size > 0 && onChunkAvailable) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64String = (reader.result as string).split(",")[1];
            if (base64String) {
              onChunkAvailable(base64String, "webm_opus");
            }
          };
          reader.readAsDataURL(event.data);
        }
      };

      mediaRecorder.start(timeslice);
      setIsRecording(true);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to access microphone.";
      setError(errorMessage);
      setIsRecording(false);
    }
  }, [onChunkAvailable, timeslice]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
  }, []);

  return {
    isRecording,
    error,
    startRecording,
    stopRecording,
  };
}
