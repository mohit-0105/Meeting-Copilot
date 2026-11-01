import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Meeting Copilot API" in data["service"]
    assert data["storage"] == "persistent_sqlite"

def test_create_and_get_meeting():
    # 1. Create Meeting
    payload = {"title": "Q4 Roadmap Brainstorm", "agenda": ["Roadmap", "Budget"]}
    res = client.post("/api/meetings", json=payload)
    assert res.status_code == 200
    meeting_data = res.json()
    meeting_id = meeting_data["id"]
    assert meeting_data["title"] == "Q4 Roadmap Brainstorm"
    assert meeting_data["status"] == "active"
    assert "Roadmap" in meeting_data["agenda"]

    # 2. Get Meeting
    get_res = client.get(f"/api/meetings/{meeting_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == meeting_id

def test_action_items_workflow():
    res = client.post("/api/meetings", json={"title": "Action Items Test Sync"})
    meeting_id = res.json()["id"]

    # 1. Add action item
    action_payload = {
        "title": "Setup PostgreSQL vector index",
        "assignee": "Backend Lead",
        "due_date": "Next Monday"
    }
    action_res = client.post(f"/api/meetings/{meeting_id}/action-items", json=action_payload)
    assert action_res.status_code == 200
    act_data = action_res.json()
    action_id = act_data["id"]
    assert act_data["title"] == "Setup PostgreSQL vector index"
    assert act_data["status"] == "pending"

    # 2. List action items
    list_res = client.get(f"/api/meetings/{meeting_id}/action-items")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(i["id"] == action_id for i in items)

    # 3. Patch action item to completed
    patch_res = client.patch(
        f"/api/meetings/{meeting_id}/action-items/{action_id}",
        json={"status": "completed"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"

def test_insights_agenda_and_nudges():
    res = client.post("/api/meetings", json={
        "title": "Strategy & Insights Sync",
        "agenda": ["Supply chain", "Unrelated Topic"]
    })
    meeting_id = res.json()["id"]

    # 1. Agenda tracking
    agenda_res = client.get(f"/api/meetings/{meeting_id}/agenda")
    assert agenda_res.status_code == 200
    assert agenda_res.json()["total_agenda_items"] == 2

    # 2. Insights
    insights_res = client.get(f"/api/meetings/{meeting_id}/insights")
    assert insights_res.status_code == 200
    insights_data = insights_res.json()
    assert insights_data["meeting_id"] == meeting_id
    assert "sentiment" in insights_data
    assert "engagement_score" in insights_data

    # 3. Proactive Nudges
    nudges_res = client.get(f"/api/meetings/{meeting_id}/nudges")
    assert nudges_res.status_code == 200
    assert "nudges" in nudges_res.json()

def test_audio_upload_and_search():
    res = client.post("/api/meetings", json={"title": "Audio Search Sync"})
    meeting_id = res.json()["id"]

    # 1. Upload audio
    fake_audio_file = io.BytesIO(b"RIFF....WAVEfmt ....data....")
    upload_res = client.post(
        f"/api/meetings/{meeting_id}/upload-audio",
        files={"file": ("test_recording.wav", fake_audio_file, "audio/wav")}
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["segments_added"] > 0

    # 2. Test search across meetings
    search_res = client.get("/api/search?q=roadmap")
    assert search_res.status_code == 200
    assert isinstance(search_res.json(), list)

    # 3. Test global RAG query
    rag_res = client.post("/api/copilot/global-query", json={"query": "What did Sarah say about roadmap?"})
    assert rag_res.status_code == 200
    assert "answer" in rag_res.json()

def test_end_meeting_and_multi_format_export():
    res = client.post("/api/meetings", json={"title": "Sprint Planning Session"})
    meeting_id = res.json()["id"]

    # End meeting
    end_res = client.post(f"/api/meetings/{meeting_id}/end")
    assert end_res.status_code == 200
    summary_data = end_res.json()
    assert summary_data["meeting_id"] == meeting_id
    assert "summary" in summary_data

    # 1. Export Markdown
    export_md = client.get(f"/api/meetings/{meeting_id}/export?format=markdown")
    assert export_md.status_code == 200
    assert "text/markdown" in export_md.headers["content-type"]
    assert "Meeting Notes: Sprint Planning Session" in export_md.text

    # 2. Export HTML Dashboard
    export_html = client.get(f"/api/meetings/{meeting_id}/export?format=html")
    assert export_html.status_code == 200
    assert "text/html" in export_html.headers["content-type"]
    assert "Executive Summary" in export_html.text

    # Clean up / Delete Meeting
    del_res = client.delete(f"/api/meetings/{meeting_id}")
    assert del_res.status_code == 200
