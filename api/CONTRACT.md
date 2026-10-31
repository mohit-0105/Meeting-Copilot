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
  - **Response:**
    ```json
    {
      "meeting_id": "meet_123",
      "total_duration_estimate": "14:30",
      "total_words": 1420,
      "speakers": [
        {
          "speaker": "Sarah K.",
          "segment_count": 12,
          "word_count": 780,
          "talk_time_seconds": 361,
          "talk_time_percentage": 54.9
        },
        {
          "speaker": "Dave R.",
          "segment_count": 8,
          "word_count": 410,
          "talk_time_seconds": 189,
          "talk_time_percentage": 28.9
        }
      ],
      "sentiment": "collaborative",
      "key_topics": ["Supply Chain", "Project Gamma", "Logistics"],
      "engagement_score": 88
    }
    ```

### 2.5 Agenda Tracking
- **`POST /api/meetings/{meeting_id}/agenda`**
  - **Body:** `{ "agenda": ["Q4 Roadmap", "Supply Chain Delays", "Vendor Deep Dive"] }`
  - **Response:** Agenda status response.

- **`GET /api/meetings/{meeting_id}/agenda`**
  - **Response:**
    ```json
    {
      "meeting_id": "meet_123",
      "total_agenda_items": 3,
      "completed_items": 2,
      "items": [
        { "topic": "Q4 Roadmap", "covered": true, "mentioned_at": "00:03" },
        { "topic": "Supply Chain Delays", "covered": true, "mentioned_at": "00:15" },
        { "topic": "Vendor Deep Dive", "covered": false, "mentioned_at": null }
      ]
    }
    ```

### 2.6 Audio Upload & Batch Transcription
- **`POST /api/meetings/{meeting_id}/upload-audio`**
  - **Request:** `multipart/form-data` with `file: <audio_file>`
  - **Response:**
    ```json
    {
      "meeting_id": "meet_123",
      "filename": "team_sync.webm",
      "segments_added": 3,
      "action_items_detected": 1,
      "transcript": [...]
    }
    ```

### 2.7 Meeting End & Summary
- **`POST /api/meetings/{meeting_id}/end`**
  - Triggers final AI summary generation, saves meeting state, and broadcasts to WebSocket attendees.

### 2.8 Export Meeting Notes
- **`GET /api/meetings/{meeting_id}/export?format=markdown|json`**
  - Returns formatted Markdown document or complete JSON dump suitable for Notion, Slack, and file downloads.
