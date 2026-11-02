/**
 * Meeting Copilot - Shared TypeScript Types & WebSocket Protocol Definitions
 * Single source of truth for Frontend (Next.js) and Backend (FastAPI).
 */

// ==========================================
// REST Models
// ==========================================

export type MeetingStatus = "active" | "completed";
export type ActionItemStatus = "pending" | "completed";

export interface ActionItem {
  id: string;
  title: string;
  assignee?: string;
  due_date?: string | null;
  status: ActionItemStatus;
}

export interface ActionItemCreate {
  title: string;
  assignee?: string;
  due_date?: string;
}

export interface ActionItemUpdate {
  title?: string;
  assignee?: string;
  due_date?: string;
  status?: ActionItemStatus;
}

export interface TranscriptSegment {
  id: string;
  speaker: string;
  text: string;
  timestamp: string; // e.g. "00:15"
  is_final: boolean;
}

export interface MeetingSummary {
  meeting_id: string;
  title: string;
  summary: string;
  key_points: string[];
  action_items: ActionItem[];
}

export interface SpeakerStat {
  speaker: string;
  segment_count: number;
  word_count: number;
  talk_time_seconds: number;
  talk_time_percentage: number; // e.g. 45.5 (%)
}

export interface MeetingInsights {
  meeting_id: string;
  total_duration_estimate: string;
  total_words: number;
  speakers: SpeakerStat[];
  sentiment: "positive" | "collaborative" | "neutral" | "urgent" | "mixed";
  key_topics: string[];
  engagement_score: number; // 0 to 100
}

export interface AgendaItem {
  topic: string;
  covered: boolean;
  mentioned_at?: string; // e.g. "00:15"
}

export interface AgendaCheckResponse {
  meeting_id: string;
  total_agenda_items: number;
  completed_items: number;
  items: AgendaItem[];
}

export interface NudgesResponse {
  meeting_id: string;
  nudges: string[];
}

export interface RAGSource {
  meeting_id: string;
  meeting_title: string;
  timestamp: string;
  speaker: string;
  text: string;
}

export interface RAGQueryRequest {
  query: string;
}

export interface RAGQueryResponse {
  query: string;
  answer: string;
  sources: RAGSource[];
}

export interface AudioUploadResponse {
  meeting_id: string;
  filename: string;
  segments_added: number;
  action_items_detected: number;
  transcript: TranscriptSegment[];
}

export interface SlackWebhookRequest {
  webhook_url: string;
}

export interface Meeting {
  id: string;
  title: string;
  status: MeetingStatus;
  created_at: string;
  segments: TranscriptSegment[];
  action_items: ActionItem[];
  summary?: string | null;
  agenda?: string[];
  segment_count?: number;
  action_item_count?: number;
}

export interface MeetingCreate {
  title: string;
  agenda?: string[];
}

// ==========================================
// WebSocket Message Protocol
// ==========================================

// Client -> Server
export interface WSAudioChunk {
  type: "audio_chunk";
  data: string; // Base64 encoded audio
  format?: "webm_opus" | "wav" | "pcm";
  timestamp?: string;
}

export interface WSTranscriptText {
  type: "transcript_text";
  text: string;
  speaker?: string;
  timestamp?: string;
}

export interface WSCopilotQuery {
  type: "copilot_query";
  query: string;
}

export interface WSPing {
  type: "ping";
}

export type WSClientMessage = WSAudioChunk | WSTranscriptText | WSCopilotQuery | WSPing;

// Server -> Client
export interface WSTranscriptSegment extends TranscriptSegment {
  type: "transcript_segment";
}

export interface WSCopilotResponse {
  type: "copilot_response";
  query: string;
  answer: string;
  references: string[];
}

export interface WSActionItemDetected extends ActionItem {
  type: "action_item_detected";
}

export interface WSProactiveNudge {
  type: "proactive_nudge";
  nudge: string;
}

export interface WSSyncHistory {
  type: "sync_history";
  segments: TranscriptSegment[];
  action_items: ActionItem[];
}

export interface WSPong {
  type: "pong";
}

export interface WSMeetingSummaryBroadcast extends MeetingSummary {
  type: "meeting_summary";
}

export type WSServerMessage =
  | WSTranscriptSegment
  | WSCopilotResponse
  | WSActionItemDetected
  | WSProactiveNudge
  | WSSyncHistory
  | WSPong
  | WSMeetingSummaryBroadcast;
