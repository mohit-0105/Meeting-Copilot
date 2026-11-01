from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ==========================================
# REST Schemas
# ==========================================

class ActionItem(BaseModel):
    id: str
    title: str
    assignee: Optional[str] = "Unassigned"
    due_date: Optional[str] = None
    status: Literal["pending", "completed"] = "pending"

class ActionItemCreate(BaseModel):
    title: str
    assignee: Optional[str] = "Unassigned"
    due_date: Optional[str] = None

class ActionItemUpdate(BaseModel):
    title: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[Literal["pending", "completed"]] = None

class TranscriptSegment(BaseModel):
    id: str
    speaker: str
    text: str
    timestamp: str
    is_final: bool = True

class MeetingCreate(BaseModel):
    title: str = Field(..., description="Title of the meeting")
    agenda: List[str] = []

class MeetingSummary(BaseModel):
    meeting_id: str
    title: str
    summary: str
    key_points: List[str] = []
    action_items: List[ActionItem] = []

class SpeakerStat(BaseModel):
    speaker: str
    segment_count: int
    word_count: int
    talk_time_seconds: int
    talk_time_percentage: float

class MeetingInsights(BaseModel):
    meeting_id: str
    total_duration_estimate: str
    total_words: int
    speakers: List[SpeakerStat] = []
    sentiment: Literal["positive", "collaborative", "neutral", "urgent", "mixed"] = "collaborative"
    key_topics: List[str] = []
    engagement_score: int = 85

class AgendaItem(BaseModel):
    topic: str
    covered: bool
    mentioned_at: Optional[str] = None

class AgendaCreate(BaseModel):
    agenda: List[str]

class AgendaCheckResponse(BaseModel):
    meeting_id: str
    total_agenda_items: int
    completed_items: int
    items: List[AgendaItem]

class AudioUploadResponse(BaseModel):
    meeting_id: str
    filename: str
    segments_added: int
    action_items_detected: int
    transcript: List[TranscriptSegment]

class NudgesResponse(BaseModel):
    meeting_id: str
    nudges: List[str]

class RAGQueryRequest(BaseModel):
    query: str

class RAGSource(BaseModel):
    meeting_id: str
    meeting_title: str
    timestamp: str
    speaker: str
    text: str

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[RAGSource] = []

class SlackWebhookRequest(BaseModel):
    webhook_url: str

class Meeting(BaseModel):
    id: str
    title: str
    status: Literal["active", "completed"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    segments: List[TranscriptSegment] = []
    action_items: List[ActionItem] = []
    summary: Optional[str] = None
    agenda: List[str] = []

# ==========================================
# WebSocket Message Schemas
# ==========================================

class WSAudioChunk(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # Base64 string
    format: str = "webm_opus"
    timestamp: Optional[str] = None

class WSCopilotQuery(BaseModel):
    type: Literal["copilot_query"] = "copilot_query"
    query: str

class WSPing(BaseModel):
    type: Literal["ping"] = "ping"

class WSTranscriptSegment(TranscriptSegment):
    type: Literal["transcript_segment"] = "transcript_segment"

class WSCopilotResponse(BaseModel):
    type: Literal["copilot_response"] = "copilot_response"
    query: str
    answer: str
    references: List[str] = []

class WSActionItemDetected(ActionItem):
    type: Literal["action_item_detected"] = "action_item_detected"

class WSProactiveNudge(BaseModel):
    type: Literal["proactive_nudge"] = "proactive_nudge"
    nudge: str

class WSSyncHistory(BaseModel):
    type: Literal["sync_history"] = "sync_history"
    segments: List[TranscriptSegment] = []
    action_items: List[ActionItem] = []

class WSPong(BaseModel):
    type: Literal["pong"] = "pong"
