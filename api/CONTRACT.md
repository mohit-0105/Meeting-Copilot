# 📜 Meeting Copilot - Shared API & WebSocket Contract

> **Single Source of Truth** for Person A (Frontend) and Person B (Backend).  
> Both sides adhere strictly to these schemas to allow independent development and zero-friction integration.

---

## 1. WebSocket Protocol

**Endpoint:** `ws://localhost:8000/ws/meetings/{meeting_id}`

### 1.1 Client ➔ Server Messages

#### A. Send Audio Chunk (Live speech stream)
```json
{
  "type": "audio_chunk",
  "data": "<base64_encoded_audio_data>",
  "format": "webm_opus",
  "timestamp": "00:15"
}
```

#### B. Ask Copilot Query (Live Q&A)
```json
{
  "type": "copilot_query",
  "query": "What did Sarah say about the Q4 timeline?"
}
```

#### C. Ping / Keepalive
```json
{
  "type": "ping"
}
```

---

### 1.2 Server ➔ Client Messages

#### A. Initial Sync / Reconnect (`sync_history`)
Emitted immediately upon client connection with all past transcript lines and detected action items.
```json
{
  "type": "sync_history",
  "segments": [
    {
      "id": "seg_101",
      "speaker": "Sarah K.",
      "text": "Let's review the API architecture for next sprint.",
      "timestamp": "00:15",
      "is_final": true
    }
  ],
  "action_items": [
    {
      "id": "act_201",
      "title": "Schedule deep dive on logistics",
      "assignee": "Sarah K.",
      "due_date": "Tomorrow, 2:00 PM",
      "status": "pending"
    }
  ]
}
```

#### B. Live Transcript Segment
Emitted in real-time as speech is recognized.
```json
{
  "type": "transcript_segment",
  "id": "seg_101",
  "speaker": "Sarah K.",
  "text": "Let's review the API architecture for next sprint.",
  "timestamp": "00:15",
  "is_final": true
}
```

#### C. Copilot Answer
Emitted in response to `copilot_query`.
```json
{
  "type": "copilot_response",
  "query": "What did Sarah say about the Q4 timeline?",
  "answer": "Sarah indicated that the initial rollout will be delayed due to supply chain bottlenecks, and scheduled a follow-up for tomorrow at 2 PM.",
  "references": ["00:15", "00:40"]
}
```

#### D. Action Item Detected
Emitted proactively when an action item is parsed from the conversation.
```json
{
  "type": "action_item_detected",
  "id": "act_201",
  "title": "Schedule deep dive on logistics",
  "assignee": "Sarah K.",
  "due_date": "Tomorrow, 2:00 PM",
  "status": "pending"
}
```

#### E. Meeting Summary (Upon meeting end)
```json
{
  "type": "meeting_summary",
  "meeting_id": "meet_123",
  "title": "Weekly Strategy Sync",
  "summary": "Key discussion on Q4 milestones and logistical challenges.",
  "key_points": [
    "Dave highlighted supply chain bottlenecks in Project Gamma.",
    "Logistics deep dive scheduled for tomorrow."
  ],
  "action_items": [
    {
      "id": "act_201",
      "title": "Schedule deep dive on logistics",
      "assignee": "Sarah K.",
      "due_date": "Tomorrow, 2:00 PM",
      "status": "pending"
    }
  ]
}
```

#### F. Pong / Heartbeat
```json
{
  "type": "pong"
}
```

---

## 2. REST API Endpoints

### 2.1 Health Check
- **`GET /api/health`**
- **Response:**
  ```json
  { "status": "ok", "service": "Meeting Copilot API", "version": "0.1.0" }
  ```

### 2.2 Meetings Management
- **`POST /api/meetings`**
  - **Body:** `{ "title": "Weekly Strategy Sync" }`
  - **Response:** `{ "id": "meet_123", "title": "Weekly Strategy Sync", "status": "active", "created_at": "..." }`

- **`GET /api/meetings`**
  - **Response:** `[ { "id": "meet_123", "title": "...", "status": "completed", ... } ]`

- **`GET /api/meetings/{meeting_id}`**
  - **Response:** Complete meeting detail including segments, summary, and action items.

- **`DELETE /api/meetings/{meeting_id}`**
  - **Response:** `{ "status": "success", "message": "Meeting 'meet_123' deleted." }`

### 2.3 Action Items Management
- **`GET /api/meetings/{meeting_id}/action-items`**
  - **Response:** List of action items for the meeting.

- **`POST /api/meetings/{meeting_id}/action-items`**
  - **Body:** `{ "title": "Prepare vendor quote", "assignee": "Emily", "due_date": "Friday" }`
  - **Response:** Created action item object.

- **`PATCH /api/meetings/{meeting_id}/action-items/{item_id}`**
  - **Body:** `{ "status": "completed" }` or `{ "assignee": "Sarah" }`
  - **Response:** Updated action item object.

### 2.4 Meeting End & Summary
- **`POST /api/meetings/{meeting_id}/end`**
  - Triggers final AI summary generation, saves meeting state, and broadcasts to WebSocket attendees.

### 2.5 Export Meeting Notes
- **`GET /api/meetings/{meeting_id}/export?format=markdown|json`**
  - Returns formatted Markdown document or complete JSON dump suitable for Notion, Slack, and file downloads.
