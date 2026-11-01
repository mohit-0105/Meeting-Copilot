import os
import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "meetings.db"

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(self.db_path.parent, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Meetings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    summary TEXT,
                    key_points TEXT,
                    agenda TEXT
                )
            """)

            # Transcript segments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcript_segments (
                    id TEXT PRIMARY KEY,
                    meeting_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    is_final INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                )
            """)

            # Action items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_items (
                    id TEXT PRIMARY KEY,
                    meeting_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    assignee TEXT DEFAULT 'Unassigned',
                    due_date TEXT,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                )
            """)

            # Pre-seed default sync meeting if table is empty
            cursor.execute("SELECT COUNT(*) FROM meetings")
            if cursor.fetchone()[0] == 0:
                now_str = datetime.utcnow().isoformat()
                cursor.execute("""
                    INSERT INTO meetings (id, title, status, created_at, agenda)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    "default_sync",
                    "Weekly Strategy Sync",
                    "active",
                    now_str,
                    json.dumps(["Review Q4 roadmap", "Supply chain status", "Vendor deep dive"])
                ))

            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==========================================
    # Async DB Methods
    # ==========================================

    async def create_meeting(self, meeting_id: str, title: str, agenda: List[str]) -> dict:
        def _sync():
            with self._get_connection() as conn:
                now_str = datetime.utcnow().isoformat()
                conn.execute("""
                    INSERT INTO meetings (id, title, status, created_at, agenda)
                    VALUES (?, ?, 'active', ?, ?)
                """, (meeting_id, title, now_str, json.dumps(agenda)))
                conn.commit()
                return {
                    "id": meeting_id,
                    "title": title,
                    "status": "active",
                    "created_at": now_str,
                    "agenda": agenda,
                    "segments": [],
                    "action_items": [],
                    "summary": None
                }
        return await asyncio.to_thread(_sync)

    async def get_meeting(self, meeting_id: str) -> Optional[dict]:
        def _sync():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Fetch segments
                cursor.execute("""
                    SELECT id, speaker, text, timestamp, is_final
                    FROM transcript_segments
                    WHERE meeting_id = ?
                    ORDER BY rowid ASC
                """, (meeting_id,))
                segments = [dict(r) for r in cursor.fetchall()]

                # Fetch action items
                cursor.execute("""
                    SELECT id, title, assignee, due_date, status
                    FROM action_items
                    WHERE meeting_id = ?
                    ORDER BY rowid ASC
                """, (meeting_id,))
                actions = [dict(r) for r in cursor.fetchall()]

                agenda = json.loads(row["agenda"]) if row["agenda"] else []
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "summary": row["summary"],
                    "agenda": agenda,
                    "segments": segments,
                    "action_items": actions
                }
        return await asyncio.to_thread(_sync)

    async def list_meetings(self) -> List[dict]:
        def _sync():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC")
                meetings = []
                for row in cursor.fetchall():
                    m_id = row["id"]
                    cursor.execute("SELECT COUNT(*) FROM transcript_segments WHERE meeting_id = ?", (m_id,))
                    seg_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM action_items WHERE meeting_id = ?", (m_id,))
                    act_count = cursor.fetchone()[0]

                    agenda = json.loads(row["agenda"]) if row["agenda"] else []
                    meetings.append({
                        "id": row["id"],
                        "title": row["title"],
                        "status": row["status"],
                        "created_at": row["created_at"],
                        "summary": row["summary"],
                        "agenda": agenda,
                        "segments": [],
                        "action_items": [],
                        "segment_count": seg_count,
                        "action_item_count": act_count
                    })
                return meetings
        return await asyncio.to_thread(_sync)

    async def delete_meeting(self, meeting_id: str) -> bool:
        def _sync():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transcript_segments WHERE meeting_id = ?", (meeting_id,))
                cursor.execute("DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,))
                cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
                conn.commit()
                return cursor.rowcount > 0
        return await asyncio.to_thread(_sync)

    async def save_segment(self, meeting_id: str, segment: dict):
        def _sync():
            with self._get_connection() as conn:
                now_str = datetime.utcnow().isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO transcript_segments (id, meeting_id, speaker, text, timestamp, is_final, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    segment["id"],
                    meeting_id,
                    segment["speaker"],
                    segment["text"],
                    segment.get("timestamp", "00:00"),
                    1 if segment.get("is_final", True) else 0,
                    now_str
                ))
                conn.commit()
        return await asyncio.to_thread(_sync)

    async def save_action_item(self, meeting_id: str, action: dict):
        def _sync():
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO action_items (id, meeting_id, title, assignee, due_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    action["id"],
                    meeting_id,
                    action["title"],
                    action.get("assignee", "Unassigned"),
                    action.get("due_date"),
                    action.get("status", "pending")
                ))
                conn.commit()
        return await asyncio.to_thread(_sync)

    async def update_action_item(self, action_id: str, updates: dict) -> Optional[dict]:
        def _sync():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM action_items WHERE id = ?", (action_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                title = updates.get("title") or row["title"]
                assignee = updates.get("assignee") or row["assignee"]
                due_date = updates.get("due_date") if "due_date" in updates else row["due_date"]
                status = updates.get("status") or row["status"]

                cursor.execute("""
                    UPDATE action_items
                    SET title = ?, assignee = ?, due_date = ?, status = ?
                    WHERE id = ?
                """, (title, assignee, due_date, status, action_id))
                conn.commit()
                return {
                    "id": action_id,
                    "title": title,
                    "assignee": assignee,
                    "due_date": due_date,
                    "status": status
                }
        return await asyncio.to_thread(_sync)

    async def end_meeting_with_summary(self, meeting_id: str, summary: str, key_points: List[str]):
        def _sync():
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE meetings
                    SET status = 'completed', summary = ?, key_points = ?
                    WHERE id = ?
                """, (summary, json.dumps(key_points), meeting_id))
                conn.commit()
        return await asyncio.to_thread(_sync)

    async def set_agenda(self, meeting_id: str, agenda: List[str]):
        def _sync():
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE meetings
                    SET agenda = ?
                    WHERE id = ?
                """, (json.dumps(agenda), meeting_id))
                conn.commit()
        return await asyncio.to_thread(_sync)

    async def search_all_transcripts(self, query: str) -> List[dict]:
        """Performs full-text search across all recorded meetings transcripts."""
        def _sync():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Search using SQLite LIKE matching
                cursor.execute("""
                    SELECT ts.id, ts.meeting_id, m.title as meeting_title, ts.speaker, ts.text, ts.timestamp
                    FROM transcript_segments ts
                    JOIN meetings m ON ts.meeting_id = m.id
                    WHERE ts.text LIKE ?
                    ORDER BY ts.rowid DESC
                    LIMIT 20
                """, (f"%{query}%",))
                return [dict(r) for r in cursor.fetchall()]
        return await asyncio.to_thread(_sync)

db = Database()
