import base64
import uuid
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import PlainTextResponse
from app.models.schemas import (
    Meeting,
    MeetingCreate,
    MeetingSummary,
    ActionItem,
    ActionItemCreate,
    ActionItemUpdate,
    TranscriptSegment,
    MeetingInsights,
    AgendaCreate,
    AgendaCheckResponse,
    AudioUploadResponse
)
from app.api.websocket import manager
from app.services.copilot import copilot_service
from app.services.stt import stt_service

router = APIRouter(prefix="/api", tags=["Meetings"])

# In-memory storage for meetings
meetings_db: Dict[str, Meeting] = {
    "default_sync": Meeting(
        id="default_sync",
        title="Weekly Strategy Sync",
        status="active",
        agenda=["Review Q4 roadmap", "Supply chain status", "Vendor deep dive"]
    )
}

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Meeting Copilot API",
        "version": "0.1.0"
    }

@router.post("/meetings", response_model=Meeting)
async def create_meeting(payload: MeetingCreate):
    meeting_id = f"meet_{uuid.uuid4().hex[:8]}"
    new_meeting = Meeting(
        id=meeting_id,
        title=payload.title,
        status="active",
        agenda=payload.agenda
    )
    meetings_db[meeting_id] = new_meeting
    return new_meeting

@router.get("/meetings", response_model=List[Meeting])
async def list_meetings():
    meetings_list = []
    for m in meetings_db.values():
        m_copy = m.model_copy()
        if m.id in manager.meeting_history:
            m_copy.segments = [TranscriptSegment(**s) for s in manager.meeting_history[m.id]]
        if m.id in manager.meeting_actions:
            m_copy.action_items = [ActionItem(**a) for a in manager.meeting_actions[m.id]]
        meetings_list.append(m_copy)
    return meetings_list

@router.get("/meetings/{meeting_id}", response_model=Meeting)
async def get_meeting(meeting_id: str):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Enrich with live in-memory transcripts and action items if currently active
    if meeting_id in manager.meeting_history:
        meeting.segments = [TranscriptSegment(**s) for s in manager.meeting_history[meeting_id]]
    if meeting_id in manager.meeting_actions:
        meeting.action_items = [ActionItem(**a) for a in manager.meeting_actions[meeting_id]]

    return meeting

@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str):
    if meeting_id not in meetings_db:
        raise HTTPException(status_code=404, detail="Meeting not found")
    del meetings_db[meeting_id]
    if meeting_id in manager.meeting_history:
        del manager.meeting_history[meeting_id]
    if meeting_id in manager.meeting_actions:
        del manager.meeting_actions[meeting_id]
    return {"status": "success", "message": f"Meeting '{meeting_id}' deleted."}

# ==========================================
# Action Items Sub-routes
# ==========================================

@router.get("/meetings/{meeting_id}/action-items", response_model=List[ActionItem])
async def list_action_items(meeting_id: str):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    actions_data = manager.meeting_actions.get(meeting_id, [])
    if not actions_data and meeting.action_items:
        return meeting.action_items
    return [ActionItem(**a) for a in actions_data]

@router.post("/meetings/{meeting_id}/action-items", response_model=ActionItem)
async def add_action_item(meeting_id: str, payload: ActionItemCreate):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    new_action = ActionItem(
        id=f"act_{uuid.uuid4().hex[:6]}",
        title=payload.title,
        assignee=payload.assignee or "Unassigned",
        due_date=payload.due_date,
        status="pending"
    )

    if meeting_id not in manager.meeting_actions:
        manager.meeting_actions[meeting_id] = []
    manager.meeting_actions[meeting_id].append(new_action.model_dump())
    meeting.action_items.append(new_action)

    # Broadcast new action item to live attendees
    await manager.broadcast_to_meeting(meeting_id, {
        "type": "action_item_detected",
        **new_action.model_dump()
    })

    return new_action

@router.patch("/meetings/{meeting_id}/action-items/{item_id}", response_model=ActionItem)
async def update_action_item(meeting_id: str, item_id: str, payload: ActionItemUpdate):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    actions_list = manager.meeting_actions.get(meeting_id, [])
    target_action = None

    for action_dict in actions_list:
        if action_dict.get("id") == item_id:
            if payload.title is not None:
                action_dict["title"] = payload.title
            if payload.assignee is not None:
                action_dict["assignee"] = payload.assignee
            if payload.due_date is not None:
                action_dict["due_date"] = payload.due_date
            if payload.status is not None:
                action_dict["status"] = payload.status
            target_action = ActionItem(**action_dict)
            break

    if not target_action:
        for act in meeting.action_items:
            if act.id == item_id:
                if payload.title is not None:
                    act.title = payload.title
                if payload.assignee is not None:
                    act.assignee = payload.assignee
                if payload.due_date is not None:
                    act.due_date = payload.due_date
                if payload.status is not None:
                    act.status = payload.status
                target_action = act
                break

    if not target_action:
        raise HTTPException(status_code=404, detail="Action item not found")

    return target_action

# ==========================================
# Meeting End & Summary
# ==========================================

@router.post("/meetings/{meeting_id}/end", response_model=MeetingSummary)
async def end_meeting(meeting_id: str):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    segments = manager.meeting_history.get(meeting_id, [])
    actions_data = manager.meeting_actions.get(meeting_id, [])
    action_items = [ActionItem(**a) for a in actions_data]
    
    summary = await copilot_service.generate_summary(
        meeting_id=meeting_id,
        title=meeting.title,
        segments=segments,
        action_items=action_items
    )
    
    meeting.status = "completed"
    meeting.summary = summary.summary
    meeting.segments = [TranscriptSegment(**s) for s in segments]
    meeting.action_items = action_items
    
    # Broadcast summary to any still-connected participants
    summary_msg = {
        "type": "meeting_summary",
        **summary.model_dump()
    }
    await manager.broadcast_to_meeting(meeting_id, summary_msg)
    
    return summary

# ==========================================
# Analytics & Insights
# ==========================================

@router.get("/meetings/{meeting_id}/insights", response_model=MeetingInsights)
async def get_meeting_insights(meeting_id: str):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = manager.meeting_history.get(meeting_id, [])
    if not segments and meeting.segments:
        segments = [s.model_dump() for s in meeting.segments]

    return await copilot_service.calculate_insights(meeting_id, segments)

# ==========================================
# Agenda Management & Real-time Tracker
# ==========================================

@router.post("/meetings/{meeting_id}/agenda", response_model=AgendaCheckResponse)
async def set_meeting_agenda(meeting_id: str, payload: AgendaCreate):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.agenda = payload.agenda
    segments = manager.meeting_history.get(meeting_id, [])
    if not segments and meeting.segments:
        segments = [s.model_dump() for s in meeting.segments]

    return await copilot_service.check_agenda(meeting_id, meeting.agenda, segments)

@router.get("/meetings/{meeting_id}/agenda", response_model=AgendaCheckResponse)
async def check_meeting_agenda(meeting_id: str):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = manager.meeting_history.get(meeting_id, [])
    if not segments and meeting.segments:
        segments = [s.model_dump() for s in meeting.segments]

    return await copilot_service.check_agenda(meeting_id, meeting.agenda, segments)

# ==========================================
# Audio File Upload & Batch Transcription
# ==========================================

@router.post("/meetings/{meeting_id}/upload-audio", response_model=AudioUploadResponse)
async def upload_meeting_audio(meeting_id: str, file: UploadFile = File(...)):
    meeting = meetings_db.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    content = await file.read()
    b64_data = base64.b64encode(content).decode("utf-8")

    if meeting_id not in manager.meeting_history:
        manager.meeting_history[meeting_id] = []
    if meeting_id not in manager.meeting_actions:
        manager.meeting_actions[meeting_id] = []

    # Process audio chunk / simulate transcription segments
    new_segments: List[TranscriptSegment] = []
    detected_actions = 0

    # Simulate 3 sequential chunks from the audio file
    for i in range(1, 4):
        time_str = f"0{i}:00"
        seg = await stt_service.transcribe_chunk(b64_data, current_time_str=time_str)
        if seg:
            manager.meeting_history[meeting_id].append(seg.model_dump())
            new_segments.append(seg)
            
            # Check for action item
            action = await copilot_service.detect_action_item(seg.text, seg.speaker)
            if action:
                manager.meeting_actions[meeting_id].append(action.model_dump())
                detected_actions += 1

    return AudioUploadResponse(
        meeting_id=meeting_id,
        filename=file.filename or "audio.webm",
        segments_added=len(new_segments),
        action_items_detected=detected_actions,
        transcript=new_segments
    )

# ==========================================
# Export Meeting Notes
# ==========================================

@router.get("/meetings/{meeting_id}/export")
async def export_meeting(meeting_id: str, format: str = Query("markdown", regex="^(markdown|json)$")):
    meeting = await get_meeting(meeting_id)

    if format == "json":
        return meeting

    # Markdown export format
    md_lines = [
        f"# 📋 Meeting Notes: {meeting.title}",
        f"- **Meeting ID:** `{meeting.id}`",
        f"- **Status:** `{meeting.status}`",
        f"- **Date:** {meeting.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
        "## 📝 Executive Summary",
        meeting.summary or "Summary not generated yet.",
        "\n## ✅ Action Items"
    ]

    if meeting.action_items:
        for act in meeting.action_items:
            checkbox = "[x]" if act.status == "completed" else "[ ]"
            due = f" *(Due: {act.due_date})*" if act.due_date else ""
            assignee = f" - **@{act.assignee}**" if act.assignee else ""
            md_lines.append(f"- {checkbox} {act.title}{assignee}{due}")
    else:
        md_lines.append("_No action items recorded._")

    md_lines.append("\n## 🎙️ Transcript")
    if meeting.segments:
        for seg in meeting.segments:
            md_lines.append(f"- `[{seg.timestamp}]` **{seg.speaker}**: {seg.text}")
    else:
        md_lines.append("_No transcript recorded._")

    return PlainTextResponse(content="\n".join(md_lines), media_type="text/markdown")
