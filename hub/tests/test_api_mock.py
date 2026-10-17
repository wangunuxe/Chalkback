"""TD1 验收：每个 §6.4 接口都能返回符合契约的 mock。"""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)
TEACHER = {"Authorization": "Bearer mock-token-T1"}
HEAD = {"Authorization": "Bearer mock-token-H1"}


def schema(name):
    return Draft202012Validator(json.loads((ROOT / "contracts" / f"{name}.schema.json").read_text(encoding="utf-8")))


def example(name):
    return json.loads((ROOT / "contracts" / "examples" / f"{name}.json").read_text(encoding="utf-8"))


def test_join():
    r = client.post("/api/join", json={"invite_code": "DEMO-TEACHER","display_name": "Mme Martin", "role": "teacher"})
    assert r.status_code == 200 and set(r.json()) == {"teacher_id", "token", "workspace_id"}


def test_syllabus_current_matches_contract():
    schema("syllabus").validate(client.get("/api/syllabus/current", headers=TEACHER).json())


def test_requires_token():
    assert client.get("/api/syllabus/current").status_code == 401


def test_share_and_revoke():
    r = client.post("/api/coverage", json=example("coverage_share"), headers=TEACHER)
    assert "share_id" in r.json()
    assert client.delete(f"/api/coverage/{r.json()['share_id']}", headers=TEACHER).status_code == 204


def test_only_head_approves_syllabus():
    assert client.post("/api/syllabus/fr-grammaire-4e/approve", headers=TEACHER).status_code == 403
    assert client.post("/api/syllabus/fr-grammaire-4e/approve", headers=HEAD).status_code == 200


def test_audit_matches_contract():
    for event in client.get("/api/audit", headers=TEACHER).json():
        schema("audit_event").validate(event)
