"""Without `make mock` the Hub has no demo data: no syllabus, no lessons, no courses. Every view must still load."""
import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)
TEACHER = {"Authorization": "Bearer mock-token-T1"}
HEAD = {"Authorization": "Bearer mock-token-H1"}
ADMIN = {"Authorization": "Bearer mock-token-ADM1"}


@pytest.fixture(autouse=True)
def fresh_hub(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "fresh.db")


@pytest.mark.parametrize("view,headers", [("teacher", TEACHER), ("head", HEAD), ("admin", ADMIN)])
def test_empty_board_loads_for_every_role(view, headers):
    r = client.get(f"/api/dashboard?view={view}", headers=headers)
    assert r.status_code == 200
    board = r.json()
    assert board["syllabus"] is None and board["classes"] == []
    assert board["workspace"]["workspace_id"] == "W1"
    assert client.get("/api/courses", headers=headers).json() == []
    assert client.get("/api/syllabus", headers=headers).json() == []


def test_no_syllabus_until_the_head_publishes_one():
    assert client.get("/api/syllabus/current", headers=TEACHER).status_code == 404
    r = client.post("/api/courses", json={"name": "x", "class_id": "4A", "syllabus_id": "fr-grammaire-4e"}, headers=TEACHER)
    assert r.status_code == 422
    first = {"syllabus_id": "histoire-4e", "version": 1, "status": "draft", "subject": "histoire", "level": "4e",
             "knowledge_points": [{"kp_id": "KP01", "title": "La Révolution française", "keywords": ["révolution"]}]}
    assert client.post("/api/syllabus", json=first, headers=HEAD).json()["version"] == 1
    assert client.get("/api/dashboard?view=head", headers=HEAD).json()["drafts"] == [{"syllabus_id": "histoire-4e", "version": 1}]
    client.post("/api/syllabus/histoire-4e/approve", headers=HEAD)
    assert client.get("/api/dashboard?view=teacher", headers=TEACHER).json()["syllabus"]["syllabus_id"] == "histoire-4e"


def test_admin_still_gets_invites_and_members():
    board = client.get("/api/dashboard?view=admin", headers=ADMIN).json()
    assert {i["role"] for i in board["invites"]} == {"teacher", "head", "admin"}  # test mode: the DEMO-* codes to sign in
    assert board["members"] == {}
