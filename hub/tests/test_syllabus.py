"""TD3 acceptance: a syllabus uploaded by a department head is a draft first and only takes effect after approval (A4)."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app import db
from app.main import app
from app.mock import example

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)
TEACHER = {"Authorization": "Bearer mock-token-T1"}
HEAD = {"Authorization": "Bearer mock-token-H1"}
SCHEMA = Draft202012Validator(json.loads((ROOT / "contracts" / "syllabus.schema.json").read_text(encoding="utf-8")))


def current():
    return client.get("/api/syllabus/current", headers=TEACHER).json()


def upload(syllabus, headers=HEAD):
    return client.post("/api/syllabus", json=syllabus, headers=headers)


def renamed(title):
    syllabus = example("syllabus")
    syllabus["knowledge_points"][0]["title"] = title
    return syllabus


def test_current_matches_contract():
    body = current()
    SCHEMA.validate(body)
    assert body["status"] == "approved"


def test_draft_not_effective_until_approved():
    before = current()
    version = upload(renamed("Nouveau titre")).json()["version"]
    assert version > before["version"]
    assert current() == before

    approved = client.post(f"/api/syllabus/{before['syllabus_id']}/approve", headers=HEAD).json()
    assert approved["version"] == version and approved["status"] == "approved"
    assert current() == approved
    assert current()["knowledge_points"][0]["title"] == "Nouveau titre"


def test_version_increments():
    first = upload(example("syllabus")).json()["version"]
    second = upload(example("syllabus")).json()["version"]
    assert second == first + 1


def test_hub_sets_version_and_status():
    before = current()
    body = {**example("syllabus"), "version": 999, "status": "approved"}
    assert upload(body).json()["version"] != 999
    assert current() == before


def test_invalid_syllabus_rejected():
    body = example("syllabus")
    del body["knowledge_points"]
    assert upload(body).status_code == 422


def test_teacher_cannot_upload_or_approve():
    assert upload(example("syllabus"), headers=TEACHER).status_code == 403
    assert client.post("/api/syllabus/fr-grammaire-4e/approve", headers=TEACHER).status_code == 403


def test_approve_without_draft_rejected():
    assert client.post("/api/syllabus/no-such-syllabus/approve", headers=HEAD).status_code == 404


def test_approve_writes_audit_event():
    version = upload(example("syllabus")).json()["version"]
    client.post("/api/syllabus/fr-grammaire-4e/approve", headers=HEAD)
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT * FROM audit_events WHERE action = 'approve_syllabus' AND target_id = ?",
            (f"fr-grammaire-4e@v{version}",),
        ).fetchone()
    finally:
        conn.close()
    assert row["actor_role"] == "head" and row["actor_id"] == "H1"
