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

def test_create_and_get_meeting():
    # 1. Create Meeting
    payload = {"title": "Q4 Roadmap Brainstorm"}
    res = client.post("/api/meetings", json=payload)
    assert res.status_code == 200
    meeting_data = res.json()
    meeting_id = meeting_data["id"]
    assert meeting_data["title"] == "Q4 Roadmap Brainstorm"
    assert meeting_data["status"] == "active"

    # 2. Get Meeting
    get_res = client.get(f"/api/meetings/{meeting_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == meeting_id

def test_action_items_workflow():
    # Create meeting first
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

def test_end_meeting_and_export():
    res = client.post("/api/meetings", json={"title": "Sprint Planning Session"})
    meeting_id = res.json()["id"]

    # End meeting
    end_res = client.post(f"/api/meetings/{meeting_id}/end")
    assert end_res.status_code == 200
    summary_data = end_res.json()
    assert summary_data["meeting_id"] == meeting_id
    assert "summary" in summary_data
    assert isinstance(summary_data["key_points"], list)

    # Export Markdown
    export_res = client.get(f"/api/meetings/{meeting_id}/export?format=markdown")
    assert export_res.status_code == 200
    assert "text/markdown" in export_res.headers["content-type"]
    assert f"Meeting Notes: Sprint Planning Session" in export_res.text

    # Delete Meeting
    del_res = client.delete(f"/api/meetings/{meeting_id}")
    assert del_res.status_code == 200
