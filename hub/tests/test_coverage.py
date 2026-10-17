"""TD4, TD5 acceptance: receive approved coverage data (A3), summarize by class, teacher withdrawal (A5), audit log."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.main import app
from app.mock import example

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)
T1 = {"Authorization": "Bearer mock-token-T1"}
T2 = {"Authorization": "Bearer mock-token-T2"}
HEAD = {"Authorization": "Bearer mock-token-H1"}
ADMIN = {"Authorization": "Bearer mock-token-ADM1"}
AUDIT = Draft202012Validator(json.loads((ROOT / "contracts" / "audit_event.schema.json").read_text(encoding="utf-8")))


def lesson(class_id, lesson_id, points):
    return {**example("coverage_share"), "class_id": class_id, "lesson_id": lesson_id,
            "points": [{"kp_id": k, "covered": m > 0, "minutes": m} for k, m in points.items()]}


def share(body, headers=T1):
    return client.post("/api/coverage", json=body, headers=headers)


def table(class_id, headers=T1):
    r = client.get(f"/api/coverage?class_id={class_id}", headers=headers)
    return {p["kp_id"]: (p["covered"], p["minutes"]) for p in r.json()["points"]}


def audit(headers):
    return client.get("/api/audit", headers=headers).json()


def test_sums_lessons_per_class():
    share(lesson("5A", "L-T1-20261016-1000", {"KP01": 3, "KP02": 0}))
    share(lesson("5A", "L-T1-20261017-1000", {"KP01": 2.5, "KP03": 4}))
    t = table("5A")
    assert t["KP01"] == (True, 5.5) and t["KP02"] == (False, 0) and t["KP03"] == (True, 4)
    kp_ids = [kp["kp_id"] for kp in client.get("/api/syllabus/current", headers=T1).json()["knowledge_points"]]
    assert list(t) == kp_ids  # every knowledge point of the syllabus is listed; untaught ones are False


def test_reshare_same_lesson_replaces():
    share(lesson("5B", "L-T1-20261017-1100", {"KP01": 3}))
    share(lesson("5B", "L-T1-20261017-1100", {"KP01": 4}))
    assert table("5B")["KP01"] == (True, 4)


def test_privacy_boundary_extra_fields_rejected():
    body = lesson("5C", "L-T1-20261017-1200", {"KP01": 3})
    for extra in ({"teacher_id": "T1"}, {"transcript": "bonjour"}, {"segment_ids": ["S-1"]}):
        assert share({**body, **extra}).status_code == 422
    body["points"][0]["quote"] = "texte original"
    assert share(body).status_code == 422


def test_only_teachers_share():
    assert share(lesson("5C", "L-H1-20261017-1200", {"KP01": 3}), headers=HEAD).status_code == 403


def test_class_visibility_by_role():
    share(lesson("5D", "L-T1-20261017-1300", {"KP01": 3}))
    assert client.get("/api/coverage?class_id=5D", headers=T2).status_code == 403
    assert table("5D", headers=HEAD)["KP01"] == (True, 3)
    assert table("5D", headers=ADMIN)["KP01"] == (True, 3)


def test_revoke_removes_from_table():
    share_id = share(lesson("5E", "L-T1-20261017-1400", {"KP02": 6})).json()["share_id"]
    share(lesson("5E", "L-T1-20261017-1500", {"KP01": 1}))
    assert table("5E")["KP02"] == (True, 6)
    assert client.delete(f"/api/coverage/{share_id}", headers=T1).status_code == 204
    assert table("5E")["KP02"] == (False, 0)


def test_only_owner_revokes():
    share_id = share(lesson("5F", "L-T1-20261017-1600", {"KP01": 2})).json()["share_id"]
    assert client.delete(f"/api/coverage/{share_id}", headers=T2).status_code == 403
    assert client.delete("/api/coverage/SH-missing", headers=T1).status_code == 404


def test_share_and_revoke_are_audited():
    share_id = share(lesson("5G", "L-T1-20261017-1700", {"KP01": 2})).json()["share_id"]
    client.delete(f"/api/coverage/{share_id}", headers=T1)
    actions = [(e["action"], e["actor"]["id"]) for e in audit(ADMIN) if e["target_id"] == share_id]
    assert actions == [("share_coverage", "T1"), ("revoke", "T1")]


def test_audit_filtered_by_role():
    share(lesson("5H", "L-T2-20261017-1800", {"KP01": 2}), headers=T2)
    mine = audit(T2)
    assert mine and all(e["actor"]["id"] == "T2" for e in mine)
    everyone = {e["actor"]["id"] for e in audit(ADMIN)}
    assert {"T1", "T2"} <= everyone and everyone == {e["actor"]["id"] for e in audit(HEAD)}
    for event in audit(ADMIN):
        AUDIT.validate(event)
