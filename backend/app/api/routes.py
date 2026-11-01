import base64
import uuid
from typing import List, Dict, Optional
import httpx
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import PlainTextResponse, HTMLResponse
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
    AudioUploadResponse,
    NudgesResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    SlackWebhookRequest
)
from app.db.database import db
from app.api.websocket import manager
from app.services.copilot import copilot_service
from app.services.stt import stt_service
from app.services.rag import rag_service

router = APIRouter(prefix="/api", tags=["Meetings"])

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Meeting Copilot API",
        "version": "0.1.0",
        "storage": "persistent_sqlite"
    }

# ==========================================
# Meeting Management (Persistent SQLite)
# ==========================================

@router.post("/meetings", response_model=Meeting)
async def create_meeting(payload: MeetingCreate):
    meeting_id = f"meet_{uuid.uuid4().hex[:8]}"
    created = await db.create_meeting(
        meeting_id=meeting_id,
        title=payload.title,
        agenda=payload.agenda
    )
    return created

@router.get("/meetings", response_model=List[Meeting])
async def list_meetings():
    return await db.list_meetings()

@router.get("/meetings/{meeting_id}", response_model=Meeting)
async def get_meeting(meeting_id: str):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Merge active in-memory buffer if present
    if meeting_id in manager.meeting_history and manager.meeting_history[meeting_id]:
        meeting["segments"] = [TranscriptSegment(**s) for s in manager.meeting_history[meeting_id]]
    if meeting_id in manager.meeting_actions and manager.meeting_actions[meeting_id]:
        meeting["action_items"] = [ActionItem(**a) for a in manager.meeting_actions[meeting_id]]

    return meeting

@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str):
    success = await db.delete_meeting(meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
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
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.get("action_items", [])

@router.post("/meetings/{meeting_id}/action-items", response_model=ActionItem)
async def add_action_item(meeting_id: str, payload: ActionItemCreate):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    new_action = {
        "id": f"act_{uuid.uuid4().hex[:6]}",
        "title": payload.title,
        "assignee": payload.assignee or "Unassigned",
        "due_date": payload.due_date,
        "status": "pending"
    }

    await db.save_action_item(meeting_id, new_action)
    manager.meeting_actions.setdefault(meeting_id, []).append(new_action)

    # Broadcast new action item to live attendees
    await manager.broadcast_to_meeting(meeting_id, {
        "type": "action_item_detected",
        **new_action
    })

    return new_action

@router.patch("/meetings/{meeting_id}/action-items/{item_id}", response_model=ActionItem)
async def update_action_item(meeting_id: str, item_id: str, payload: ActionItemUpdate):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = await db.update_action_item(item_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Action item not found")

    # Update in-memory cache if active
    if meeting_id in manager.meeting_actions:
        for act in manager.meeting_actions[meeting_id]:
            if act.get("id") == item_id:
                act.update(updates)

    return updated

# ==========================================
# Meeting End & Summary
# ==========================================

@router.post("/meetings/{meeting_id}/end", response_model=MeetingSummary)
async def end_meeting(meeting_id: str):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    segments = manager.meeting_history.get(meeting_id, meeting.get("segments", []))
    action_items = [ActionItem(**a) for a in manager.meeting_actions.get(meeting_id, meeting.get("action_items", []))]
    
    summary = await copilot_service.generate_summary(
        meeting_id=meeting_id,
        title=meeting["title"],
        segments=segments,
        action_items=action_items
    )
    
    await db.end_meeting_with_summary(
        meeting_id=meeting_id,
        summary=summary.summary,
        key_points=summary.key_points
    )
    
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
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = manager.meeting_history.get(meeting_id, meeting.get("segments", []))
    return await copilot_service.calculate_insights(meeting_id, segments)

# ==========================================
# Agenda Management & Real-time Tracker
# ==========================================

@router.post("/meetings/{meeting_id}/agenda", response_model=AgendaCheckResponse)
async def set_meeting_agenda(meeting_id: str, payload: AgendaCreate):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    await db.set_agenda(meeting_id, payload.agenda)
    segments = manager.meeting_history.get(meeting_id, meeting.get("segments", []))
    return await copilot_service.check_agenda(meeting_id, payload.agenda, segments)

@router.get("/meetings/{meeting_id}/agenda", response_model=AgendaCheckResponse)
async def check_meeting_agenda(meeting_id: str):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    agenda = meeting.get("agenda", [])
    segments = manager.meeting_history.get(meeting_id, meeting.get("segments", []))
    return await copilot_service.check_agenda(meeting_id, agenda, segments)

# ==========================================
# Proactive Facilitator Nudges
# ==========================================

@router.get("/meetings/{meeting_id}/nudges", response_model=NudgesResponse)
async def get_meeting_nudges(meeting_id: str):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = manager.meeting_history.get(meeting_id, meeting.get("segments", []))
    nudges = await copilot_service.generate_nudges(
        meeting_id=meeting_id,
        segments=segments,
        agenda=meeting.get("agenda", [])
    )
    return NudgesResponse(meeting_id=meeting_id, nudges=nudges)

# ==========================================
# Cross-Meeting RAG Search & Knowledge Base
# ==========================================

@router.get("/search")
async def search_meetings(q: str = Query(..., min_length=2)):
    """Search transcripts across all past meetings with citations."""
    return await rag_service.search_meetings(q)

@router.post("/copilot/global-query", response_model=RAGQueryResponse)
async def global_copilot_query(payload: RAGQueryRequest):
    """Answers high-level questions synthesizing information from multiple past meetings."""
    return await rag_service.answer_cross_meeting_query(payload.query)

# ==========================================
# Audio File Upload & Batch Transcription
# ==========================================

@router.post("/meetings/{meeting_id}/upload-audio", response_model=AudioUploadResponse)
async def upload_meeting_audio(meeting_id: str, file: UploadFile = File(...)):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    content = await file.read()
    b64_data = base64.b64encode(content).decode("utf-8")

    new_segments: List[TranscriptSegment] = []
    detected_actions = 0

    for i in range(1, 4):
        time_str = f"0{i}:00"
        seg = await stt_service.transcribe_chunk(b64_data, current_time_str=time_str)
        if seg:
            seg_dict = seg.model_dump()
            manager.meeting_history.setdefault(meeting_id, []).append(seg_dict)
            await db.save_segment(meeting_id, seg_dict)
            new_segments.append(seg)
            
            action = await copilot_service.detect_action_item(seg.text, seg.speaker)
            if action:
                act_dict = action.model_dump()
                manager.meeting_actions.setdefault(meeting_id, []).append(act_dict)
                await db.save_action_item(meeting_id, act_dict)
                detected_actions += 1

    return AudioUploadResponse(
        meeting_id=meeting_id,
        filename=file.filename or "audio.webm",
        segments_added=len(new_segments),
        action_items_detected=detected_actions,
        transcript=new_segments
    )

# ==========================================
# Export Meeting Notes & Slack Dispatcher
# ==========================================

@router.get("/meetings/{meeting_id}/export")
async def export_meeting(meeting_id: str, format: str = Query("markdown", regex="^(markdown|json|html)$")):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = manager.meeting_history.get(meeting_id, meeting.get("segments", []))
    actions = [ActionItem(**a) for a in manager.meeting_actions.get(meeting_id, meeting.get("action_items", []))]
    summary_text = meeting.get("summary") or "Executive summary not generated yet."

    if format == "json":
        return meeting

    if format == "html":
        key_points = meeting.get("key_points") or [
            "Project roadmap and timeline review completed.",
            "Action items assigned for upcoming deliverables."
        ]
        html_content = copilot_service.export_html(
            meeting_title=meeting["title"],
            meeting_id=meeting["id"],
            summary_text=summary_text,
            key_points=key_points,
            action_items=actions,
            segments=segments
        )
        return HTMLResponse(content=html_content)

    # Markdown export
    md_lines = [
        f"# 📋 Meeting Notes: {meeting['title']}",
        f"- **Meeting ID:** `{meeting['id']}`",
        f"- **Status:** `{meeting['status']}`",
        f"- **Date:** {meeting['created_at']}\n",
        "## 📝 Executive Summary",
        summary_text,
        "\n## ✅ Action Items"
    ]

    if actions:
        for act in actions:
            checkbox = "[x]" if act.status == "completed" else "[ ]"
            due = f" *(Due: {act.due_date})*" if act.due_date else ""
            assignee = f" - **@{act.assignee}**" if act.assignee else ""
            md_lines.append(f"- {checkbox} {act.title}{assignee}{due}")
    else:
        md_lines.append("_No action items recorded._")

    md_lines.append("\n## 🎙️ Transcript")
    if segments:
        for seg in segments:
            md_lines.append(f"- `[{seg.get('timestamp','00:00')}]` **{seg.get('speaker','Speaker')}**: {seg.get('text','')}")
    else:
        md_lines.append("_No transcript recorded._")

    return PlainTextResponse(content="\n".join(md_lines), media_type="text/markdown")

@router.post("/meetings/{meeting_id}/notify-slack")
async def notify_slack(meeting_id: str, payload: SlackWebhookRequest):
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    actions = [ActionItem(**a) for a in manager.meeting_actions.get(meeting_id, meeting.get("action_items", []))]
    summary_text = meeting.get("summary") or "Meeting completed successfully."

    slack_body = copilot_service.format_slack_blocks(
        meeting_title=meeting["title"],
        summary_text=summary_text,
        action_items=actions
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(payload.webhook_url, json=slack_body)
            return {
                "status": "success",
                "slack_status_code": resp.status_code,
                "message": "Slack notification dispatched successfully."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post to Slack: {str(e)}")
