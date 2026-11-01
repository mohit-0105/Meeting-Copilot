import json
import logging
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from app.services.stt import stt_service
from app.services.copilot import copilot_service
from app.db.database import db
from app.models.schemas import (
    WSTranscriptSegment,
    WSActionItemDetected,
    WSCopilotResponse,
    WSProactiveNudge,
    WSSyncHistory,
    WSPong,
    TranscriptSegment,
    ActionItem
)

logger = logging.getLogger("meeting-copilot.ws")

class ConnectionManager:
    def __init__(self):
        # meeting_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # in-memory cache for ultra-low latency live broadcasting
        self.meeting_history: Dict[str, List[dict]] = {}
        self.meeting_actions: Dict[str, List[dict]] = {}

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        if meeting_id not in self.active_connections:
            self.active_connections[meeting_id] = []
        self.active_connections[meeting_id].append(websocket)
        logger.info(f"Client connected to meeting '{meeting_id}'. Total: {len(self.active_connections[meeting_id])}")

        # Fetch meeting from DB to sync full persistent history
        meeting = await db.get_meeting(meeting_id)
        if meeting:
            self.meeting_history[meeting_id] = meeting.get("segments", [])
            self.meeting_actions[meeting_id] = meeting.get("action_items", [])
        else:
            if meeting_id not in self.meeting_history:
                self.meeting_history[meeting_id] = []
                self.meeting_actions[meeting_id] = []

        history_segments = [TranscriptSegment(**s) for s in self.meeting_history.get(meeting_id, [])]
        history_actions = [ActionItem(**a) for a in self.meeting_actions.get(meeting_id, [])]
        sync_payload = WSSyncHistory(
            segments=history_segments,
            action_items=history_actions
        )
        await websocket.send_text(sync_payload.model_dump_json())

    def disconnect(self, meeting_id: str, websocket: WebSocket):
        if meeting_id in self.active_connections:
            if websocket in self.active_connections[meeting_id]:
                self.active_connections[meeting_id].remove(websocket)
            if not self.active_connections[meeting_id]:
                del self.active_connections[meeting_id]
        logger.info(f"Client disconnected from meeting '{meeting_id}'.")

    async def broadcast_to_meeting(self, meeting_id: str, message: dict):
        if meeting_id in self.active_connections:
            for connection in self.active_connections[meeting_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

async def handle_meeting_websocket(websocket: WebSocket, meeting_id: str):
    await manager.connect(meeting_id, websocket)
    chunk_counter = len(manager.meeting_history.get(meeting_id, []))
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
                continue

            msg_type = msg.get("type")

            # 1. Ping / Heartbeat
            if msg_type == "ping":
                await websocket.send_text(WSPong().model_dump_json())

            # 2. Audio Chunk Streaming
            elif msg_type == "audio_chunk":
                chunk_counter += 1
                audio_data = msg.get("data", "")
                audio_format = msg.get("format", "webm_opus")
                
                minutes = (chunk_counter * 15) // 60
                seconds = (chunk_counter * 15) % 60
                derived_timestamp = msg.get("timestamp") or f"{minutes:02d}:{seconds:02d}"

                segment = await stt_service.transcribe_chunk(
                    audio_data=audio_data,
                    current_time_str=derived_timestamp,
                    audio_format=audio_format
                )

                if segment:
                    # Save to memory and persistent SQLite database
                    seg_dict = segment.model_dump()
                    manager.meeting_history.setdefault(meeting_id, []).append(seg_dict)
                    await db.save_segment(meeting_id, seg_dict)

                    # Broadcast segment to all participants
                    ws_segment = WSTranscriptSegment(**seg_dict)
                    await manager.broadcast_to_meeting(meeting_id, ws_segment.model_dump())

                    # Analyze segment for action items
                    action_item = await copilot_service.detect_action_item(
                        text=segment.text,
                        speaker=segment.speaker
                    )
                    if action_item:
                        act_dict = action_item.model_dump()
                        manager.meeting_actions.setdefault(meeting_id, []).append(act_dict)
                        await db.save_action_item(meeting_id, act_dict)

                        ws_action = WSActionItemDetected(**act_dict)
                        await manager.broadcast_to_meeting(meeting_id, ws_action.model_dump())

                    # Check for proactive facilitator nudges every 3rd chunk
                    if chunk_counter % 3 == 0:
                        meeting_data = await db.get_meeting(meeting_id) or {}
                        agenda = meeting_data.get("agenda", [])
                        nudges = await copilot_service.generate_nudges(
                            meeting_id=meeting_id,
                            segments=manager.meeting_history[meeting_id],
                            agenda=agenda
                        )
                        if nudges:
                            nudge_msg = WSProactiveNudge(nudge=nudges[0])
                            await manager.broadcast_to_meeting(meeting_id, nudge_msg.model_dump())

            # 3. Real-time Copilot Query
            elif msg_type == "copilot_query":
                query = msg.get("query", "")
                history = manager.meeting_history.get(meeting_id, [])
                response = await copilot_service.answer_query(query, history)
                await websocket.send_text(response.model_dump_json())

            else:
                await websocket.send_text(json.dumps({"error": f"Unknown message type '{msg_type}'"}))

    except WebSocketDisconnect:
        manager.disconnect(meeting_id, websocket)
