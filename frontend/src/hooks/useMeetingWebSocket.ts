"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  TranscriptSegment,
  ActionItem,
  WSCopilotResponse,
  WSServerMessage,
} from "../types/meeting";

const DEFAULT_WS_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

interface UseMeetingWebSocketProps {
  meetingId: string;
  baseUrl?: string;
}

export function useMeetingWebSocket({
  meetingId,
  baseUrl = DEFAULT_WS_URL,
}: UseMeetingWebSocketProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [nudge, setNudge] = useState<string | null>(null);
  const [copilotHistory, setCopilotHistory] = useState<WSCopilotResponse[]>([]);
  const [isAsking, setIsAsking] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${baseUrl}/ws/meetings/${meetingId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log(`[WS] Connected to meeting ${meetingId}`);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSServerMessage = JSON.parse(event.data);

        switch (msg.type) {
          case "sync_history":
            setSegments(msg.segments || []);
            setActionItems(msg.action_items || []);
            break;

          case "transcript_segment":
            setSegments((prev) => [...prev, msg]);
            break;

          case "action_item_detected":
            setActionItems((prev) => {
              if (prev.some((a) => a.id === msg.id)) return prev;
              return [...prev, msg];
            });
            break;

          case "proactive_nudge":
            setNudge(msg.nudge);
            break;

          case "copilot_response":
            setCopilotHistory((prev) => [...prev, msg]);
            setIsAsking(false);
            break;

          default:
            break;
        }
      } catch (err) {
        console.error("[WS] Parse error:", err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log("[WS] Disconnected, attempting reconnect in 3s...");
      reconnectTimeoutRef.current = setTimeout(() => connectRef.current(), 3000);
    };

    ws.onerror = (err) => {
      console.error("[WS] Socket error:", err);
      ws.close();
    };
  }, [baseUrl, meetingId]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  const sendAudioChunk = useCallback((base64Data: string, format = "webm_opus") => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "audio_chunk",
          data: base64Data,
          format,
        })
      );
    }
  }, []);

  const sendTranscriptText = useCallback((text: string, speaker = "You") => {
    if (socketRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      socketRef.current.send(
        JSON.stringify({
          type: "transcript_text",
          text: text.trim(),
          speaker,
        })
      );
    }
  }, []);

  const askCopilot = useCallback((query: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN && query.trim()) {
      setIsAsking(true);
      socketRef.current.send(
        JSON.stringify({
          type: "copilot_query",
          query: query.trim(),
        })
      );
    }
  }, []);

  return {
    isConnected,
    segments,
    actionItems,
    setActionItems,
    nudge,
    copilotHistory,
    isAsking,
    sendAudioChunk,
    sendTranscriptText,
    askCopilot,
  };
}

