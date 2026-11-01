"use client";

import React, { useState, useRef, useEffect } from "react";
import { useMeetingWebSocket } from "../hooks/useMeetingWebSocket";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { ActionItem, MeetingSummary } from "../types/meeting";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MEETING_ID = "default_sync";

export default function MeetingCopilot() {
  const [queryInput, setQueryInput] = useState("");
  const [meetingSummary, setMeetingSummary] = useState<MeetingSummary | null>(null);
  const [isEnding, setIsEnding] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // WebSocket hook
  const {
    isConnected,
    segments,
    actionItems,
    setActionItems,
    nudge,
    copilotHistory,
    isAsking,
    sendAudioChunk,
    askCopilot,
  } = useMeetingWebSocket({ meetingId: MEETING_ID });

  // Audio Recorder hook
  const { isRecording, error: micError, startRecording, stopRecording } = useAudioRecorder({
    onChunkAvailable: (data, format) => {
      sendAudioChunk(data, format);
    },
    timeslice: 3000,
  });

  // Auto-scroll transcript feed
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [segments]);

  // Handle Action Item Status Toggle
  const handleToggleAction = async (item: ActionItem) => {
    const newStatus = item.status === "completed" ? "pending" : "completed";
    setActionItems((prev) =>
      prev.map((a) => (a.id === item.id ? { ...a, status: newStatus } : a))
    );

    try {
      await fetch(`${API_BASE}/api/meetings/${MEETING_ID}/action-items/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (err) {
      console.error("Failed to update action item:", err);
    }
  };

  // Handle Copilot Query Submit
  const handleQuerySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim() || isAsking) return;
    askCopilot(queryInput);
    setQueryInput("");
  };

  // Handle End Meeting
  const handleEndMeeting = async () => {
    setIsEnding(true);
    try {
      const res = await fetch(`${API_BASE}/api/meetings/${MEETING_ID}/end`, {
        method: "POST",
      });
      if (res.ok) {
        const data: MeetingSummary = await res.json();
        setMeetingSummary(data);
        if (isRecording) stopRecording();
      }
    } catch (err) {
      console.error("Failed to end meeting:", err);
    } finally {
      setIsEnding(false);
    }
  };

  // Handle Export Download
  const handleExport = (format: "markdown" | "html") => {
    window.open(`${API_BASE}/api/meetings/${MEETING_ID}/export?format=${format}`, "_blank");
  };

  // Speaker Color Map
  const getSpeakerColor = (speaker: string) => {
    if (speaker.includes("Sarah")) return "text-blue-600";
    if (speaker.includes("Dave")) return "text-emerald-600";
    if (speaker.includes("Emily")) return "text-purple-600";
    return "text-indigo-600";
  };

  return (
    <div className="flex h-screen w-full bg-slate-50 font-sans text-slate-900">
      {/* 1. Left Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col justify-between shrink-0">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow">
              M
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">Meeting Copilot</h1>
          </div>

          <nav className="space-y-1">
            <NavItem label="Dashboard" icon="📊" />
            <NavItem label="Active Meeting" icon="🎙️" active />
            <div className="ml-6 mt-2 space-y-1 border-l border-slate-700 pl-4 py-1">
              <span className="block text-xs text-blue-400 font-medium py-1">Strategy Sync</span>
            </div>
            <NavItem label="Past Meetings" icon="📅" />
            <NavItem label="Recordings" icon="📼" />
            <NavItem label="Knowledge Base" icon="🔍" />
          </nav>
        </div>

        <div className="p-6 border-t border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Status:</span>
            <span className={`flex items-center gap-1.5 font-medium ${isConnected ? "text-emerald-400" : "text-amber-400"}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-500" : "bg-amber-500 animate-pulse"}`} />
              {isConnected ? "WS Connected" : "Connecting..."}
            </span>
          </div>
        </div>
      </aside>

      {/* 2. Center Panel (Live Transcript) */}
      <main className="flex-1 flex flex-col bg-white min-w-0 border-r border-slate-200 shadow-sm z-10">
        {/* Header */}
        <header className="h-20 border-b border-slate-200 bg-white flex items-center justify-between px-8 shrink-0">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Weekly Strategy Sync</h2>
            <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${isRecording ? "bg-red-500 animate-pulse" : "bg-slate-400"}`} />
                {isRecording ? "Live Mic Recording" : "Mic Standby"}
              </span>
              <span>•</span>
              <span>ID: <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">{MEETING_ID}</code></span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleExport("html")}
              className="px-3.5 py-2 text-sm font-medium text-slate-700 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 transition"
            >
              Export HTML
            </button>
            <button
              onClick={() => handleExport("markdown")}
              className="px-3.5 py-2 text-sm font-medium text-slate-700 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 transition"
            >
              Export MD
            </button>
            <button
              onClick={handleEndMeeting}
              disabled={isEnding}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg shadow-sm hover:bg-red-700 transition disabled:opacity-50"
            >
              {isEnding ? "Ending..." : "End Meeting"}
            </button>
          </div>
        </header>

        {/* Proactive Facilitator Nudge Banner */}
        {nudge && (
          <div className="bg-amber-50 border-b border-amber-200 px-8 py-3 flex items-center gap-3 text-sm text-amber-800 animate-fade-in">
            <span className="text-base">💡</span>
            <div className="flex-1">
              <strong>Facilitator Nudge:</strong> {nudge}
            </div>
          </div>
        )}

        {/* Live Transcript Feed */}
        <div className="flex-1 overflow-y-auto p-8 space-y-5">
          {segments.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3">
              <span className="text-4xl">🎙️</span>
              <p className="text-sm">Meeting stream active. Click Start Recording to stream speech!</p>
            </div>
          ) : (
            segments.map((seg) => (
              <div key={seg.id} className="flex gap-4 group">
                <div className="w-12 text-xs font-mono text-slate-400 pt-1 shrink-0">{seg.timestamp}</div>
                <div>
                  <span className={`font-semibold text-sm ${getSpeakerColor(seg.speaker)}`}>
                    {seg.speaker}
                  </span>
                  <p className="text-slate-700 mt-0.5 leading-relaxed text-[15px]">{seg.text}</p>
                </div>
              </div>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>

        {/* Audio Recording Controls */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold shadow transition ${
                isRecording
                  ? "bg-red-600 hover:bg-red-700 text-white animate-pulse"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              <span>{isRecording ? "⏹️" : "🎙️"}</span>
              <span>{isRecording ? "Stop Recording" : "Start Microphone"}</span>
            </button>

            <button
              onClick={() => sendAudioChunk("simulated_chunk_" + Date.now())}
              className="px-3.5 py-2.5 bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-lg text-sm font-medium transition"
            >
              Simulate Speech Chunk
            </button>
          </div>

          {micError && <span className="text-xs text-red-600 font-medium">{micError}</span>}
        </div>
      </main>

      {/* 3. Right Panel (AI Copilot & Insights) */}
      <aside className="w-96 bg-slate-50 flex flex-col shrink-0">
        <div className="h-20 border-b border-slate-200 bg-slate-50 flex items-center px-6 shrink-0">
          <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            ✨ AI Copilot Insights
          </h3>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Action Items Checklist */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Action Items ({actionItems.length})
              </h4>
            </div>

            {actionItems.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No action items detected yet.</p>
            ) : (
              <div className="space-y-2.5">
                {actionItems.map((item) => (
                  <div
                    key={item.id}
                    className="flex gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-sm hover:shadow transition"
                  >
                    <input
                      type="checkbox"
                      checked={item.status === "completed"}
                      onChange={() => handleToggleAction(item)}
                      className="mt-1 w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${item.status === "completed" ? "line-through text-slate-400" : "text-slate-800"}`}>
                        {item.title}
                      </p>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                        <span>👤 {item.assignee}</span>
                        {item.due_date && <span>📅 {item.due_date}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <hr className="border-slate-200" />

          {/* Copilot Q&A History */}
          <section>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Live Copilot Q&A
            </h4>
            <div className="space-y-4">
              {copilotHistory.length === 0 ? (
                <p className="text-xs text-slate-400 italic">Ask Copilot any question about this meeting below.</p>
              ) : (
                copilotHistory.map((item, idx) => (
                  <div key={idx} className="bg-white p-3.5 rounded-lg border border-slate-200 space-y-2">
                    <p className="text-xs font-semibold text-slate-500">Q: {item.query}</p>
                    <p className="text-sm text-slate-800 leading-relaxed">{item.answer}</p>
                    {item.references && item.references.length > 0 && (
                      <div className="flex gap-1.5 pt-1">
                        {item.references.map((ref, rIdx) => (
                          <span key={rIdx} className="text-[11px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-mono">
                            ⏱️ {ref}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        {/* Copilot Chat Input */}
        <div className="p-4 bg-white border-t border-slate-200">
          <form onSubmit={handleQuerySubmit} className="relative">
            <input
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Ask Copilot about meeting..."
              disabled={isAsking}
              className="w-full pl-4 pr-10 py-2.5 text-sm border border-slate-300 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition"
            />
            <button
              type="submit"
              disabled={isAsking || !queryInput.trim()}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-blue-600 disabled:opacity-30 transition"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 2L11 13" /><path d="M22 2L15 22L11 13L2 9L22 2Z" />
              </svg>
            </button>
          </form>
        </div>
      </aside>

      {/* Meeting Summary Modal */}
      {meetingSummary && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-white max-w-2xl w-full rounded-2xl shadow-2xl p-8 space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b pb-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Executive Meeting Summary</h3>
                <p className="text-xs text-slate-500 mt-1">Generated by Meeting Copilot AI</p>
              </div>
              <button
                onClick={() => setMeetingSummary(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Summary</h4>
                <p className="text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
                  {meetingSummary.summary}
                </p>
              </div>

              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Key Takeaways</h4>
                <ul className="list-disc list-inside space-y-1.5 text-sm text-slate-700">
                  {meetingSummary.key_points.map((pt, i) => (
                    <li key={i}>{pt}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <button
                onClick={() => handleExport("html")}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition"
              >
                Download Full Report (HTML)
              </button>
              <button
                onClick={() => setMeetingSummary(null)}
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-200 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function NavItem({ label, icon, active = false }: { label: string; icon: string; active?: boolean }) {
  return (
    <a
      href="#"
      className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
        active ? "bg-slate-800 text-white font-medium" : "text-slate-400 hover:bg-slate-800/60 hover:text-white"
      }`}
    >
      <span>{icon}</span>
      <span className="text-sm">{label}</span>
    </a>
  );
}
