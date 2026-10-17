"""TD2 验收：三种角色各能用自己的邀请码加入，拿到的 token 对应正确角色。"""
import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.mock import example

client = TestClient(app)


def join(code, role, name="Test"):
    return client.post("/api/join", json={"invite_code": code, "display_name": name, "role": role})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("code,role,prefix", [
    ("DEMO-TEACHER", "teacher", "T"),
    ("DEMO-HEAD", "head", "H"),
    ("DEMO-ADMIN", "admin", "ADM"),
])
def test_each_role_can_join(code, role, prefix):
    r = join(code, role)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"teacher_id", "token", "workspace_id"}
    assert body["teacher_id"].startswith(prefix) and body["workspace_id"] == "W1"
    assert not body["token"].startswith("mock-token-")


def test_token_carries_role():
    teacher = join("DEMO-TEACHER", "teacher").json()["token"]
    head = join("DEMO-HEAD", "head").json()["token"]
    admin = join("DEMO-ADMIN", "admin").json()["token"]
    assert client.get("/api/syllabus/current", headers=auth(teacher)).status_code == 200
    assert client.post("/api/syllabus", json=example("syllabus"), headers=auth(teacher)).status_code == 403
    assert client.post("/api/syllabus", json=example("syllabus"), headers=auth(head)).status_code == 200
    assert client.get("/api/dashboard?view=admin", headers=auth(admin)).status_code == 200
    assert client.get("/api/dashboard?view=admin", headers=auth(teacher)).status_code == 403


def test_unknown_code_rejected():
    assert join("NOPE", "teacher").status_code == 404


def test_code_role_mismatch_rejected():
    assert join("DEMO-TEACHER", "admin").status_code == 403


def test_unknown_token_rejected():
    assert client.get("/api/syllabus/current", headers=auth("not-a-token")).status_code == 401


def test_mock_tokens_can_be_disabled(monkeypatch):
    assert client.get("/api/syllabus/current", headers=auth("mock-token-T1")).status_code == 200
    monkeypatch.setenv("HUB_MOCK_AUTH", "0")
    assert client.get("/api/syllabus/current", headers=auth("mock-token-T1")).status_code == 401


def test_join_writes_audit_event():
    member_id = join("DEMO-TEACHER", "teacher").json()["teacher_id"]
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM audit_events WHERE actor_id = ?", (member_id,)).fetchone()
    finally:
        conn.close()
    assert row["action"] == "join" and row["actor_role"] == "teacher" and row["workspace_id"] == "W1"
