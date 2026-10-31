from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# ==========================================
# REST Schemas
# ==========================================

class MeetingCreate(BaseModel):
    title: str = Field(..., description="Title of the meeting")

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

class MeetingSummary(BaseModel):
    meeting_id: str
    title: str
    summary: str
    key_points: List[str] = []
    action_items: List[ActionItem] = []

class Meeting(BaseModel):
    id: str
    title: str
    status: Literal["active", "completed"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    segments: List[TranscriptSegment] = []
    action_items: List[ActionItem] = []
    summary: Optional[str] = None

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

class WSSyncHistory(BaseModel):
    type: Literal["sync_history"] = "sync_history"
    segments: List[TranscriptSegment] = []
    action_items: List[ActionItem] = []

class WSPong(BaseModel):
    type: Literal["pong"] = "pong"
