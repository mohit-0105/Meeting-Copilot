# 📜 Meeting Copilot - Shared API & WebSocket Contract

> **Single Source of Truth** for Person A (Frontend) and Person B (Backend).  
> Both sides adhere strictly to these schemas to allow independent development and zero-friction integration.  
> 💡 **TypeScript Definitions:** See [`api/types.ts`](./types.ts) for ready-to-use TypeScript interfaces.

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

#### E. Proactive Nudge
Emitted periodically to assist the meeting facilitator with strategic suggestions or agenda warnings.
```json
{
  "type": "proactive_nudge",
  "nudge": "Ask the team: 'What is the immediate contingency plan if the delay extends by 2 weeks?'"
}
```

#### F. Meeting Summary (Upon meeting end)
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

#### G. Pong / Heartbeat
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
  { "status": "ok", "service": "Meeting Copilot API", "version": "0.1.0", "storage": "persistent_sqlite" }
  ```

### 2.2 Meetings Management
- **`POST /api/meetings`**
  - **Body:** `{ "title": "Weekly Strategy Sync", "agenda": ["Q4 Roadmap", "API Architecture"] }`
  - **Response:** `{ "id": "meet_123", "title": "Weekly Strategy Sync", "status": "active", "created_at": "...", "agenda": [...] }`

- **`GET /api/meetings`**
  - **Response:** `[ { "id": "meet_123", "title": "...", "status": "completed", ... } ]`

- **`GET /api/meetings/{meeting_id}`**
  - **Response:** Complete meeting detail including segments, summary, action items, and agenda.

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

### 2.4 Analytics & Speaker Insights
- **`GET /api/meetings/{meeting_id}/insights`**
  - **Response:** Speaker talk-time distribution (seconds & percentage), dialogue counts, meeting sentiment, and engagement score.

### 2.5 Agenda Tracking
- **`POST /api/meetings/{meeting_id}/agenda`**
  - **Body:** `{ "agenda": ["Q4 Roadmap", "Supply Chain Delays", "Vendor Deep Dive"] }`

- **`GET /api/meetings/{meeting_id}/agenda`**
  - **Response:** Agenda completion checklist comparing topics against the transcript.

### 2.6 Proactive Facilitator Nudges
- **`GET /api/meetings/{meeting_id}/nudges`**
  - **Response:** List of dynamic suggestions and follow-up questions for the live session.

### 2.7 Cross-Meeting RAG Search & Knowledge Base
- **`GET /api/search?q={query}`**
  - Searches historical transcripts across all meetings with relevance scoring and timestamp references.

- **`POST /api/copilot/global-query`**
  - **Body:** `{ "query": "Across all meetings, what were our main supply chain bottlenecks?" }`
  - **Response:** Synthesized AI answer referencing historical meeting titles, speakers, and quotes.

### 2.8 Audio Upload & Batch Transcription
- **`POST /api/meetings/{meeting_id}/upload-audio`**
  - **Request:** `multipart/form-data` with `file: <audio_file>`
  - Returns generated transcript segments and automatically detected action items.

### 2.9 Meeting End & Summary
- **`POST /api/meetings/{meeting_id}/end`**
  - Triggers final AI summary generation, saves meeting state permanently, and broadcasts to WebSocket attendees.

### 2.10 Multi-Format Export & Integrations
- **`GET /api/meetings/{meeting_id}/export?format=markdown|json|html`**
  - `html`: Styled, responsive executive summary dashboard suitable for printing and PDF generation.
  - `markdown`: Formatted notes ready for Notion/GitHub.
  - `json`: Complete raw data dump.

- **`POST /api/meetings/{meeting_id}/notify-slack`**
  - **Body:** `{ "webhook_url": "https://hooks.slack.com/services/..." }`
  - Dispatches meeting summary and action items to Slack channels using Slack Block Kit formatting.
