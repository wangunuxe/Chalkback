"""TD6 acceptance: after switching roles, the visible content matches the §4 permission table; pre-exam alerts follow the rule."""
from fastapi.testclient import TestClient

from app.main import app
from app.mock import example

client = TestClient(app)
T5 = {"Authorization": "Bearer mock-token-T5"}
T6 = {"Authorization": "Bearer mock-token-T6"}
HEAD = {"Authorization": "Bearer mock-token-H1"}
ADMIN = {"Authorization": "Bearer mock-token-ADM1"}


def share(class_id, lesson_id, points, headers):
    body = {**example("coverage_share"), "class_id": class_id, "lesson_id": lesson_id,
            "points": [{"kp_id": k, "covered": True, "minutes": 3} for k in points]}
    assert client.post("/api/coverage", json=body, headers=headers).status_code == 200


def board(view, headers):
    r = client.get(f"/api/dashboard?view={view}", headers=headers)
    assert r.status_code == 200
    return r.json()


def by_class(result):
    return {c["class_id"]: c for c in result["classes"]}


share("6A", "L-T5-20261017-0800", ["KP01"], T5)
share("6B", "L-T6-20261017-0800", ["KP01", "KP02"], T6)


def test_view_must_match_role():
    for view, headers in (("head", T5), ("admin", T5), ("teacher", HEAD), ("head", ADMIN)):
        assert client.get(f"/api/dashboard?view={view}", headers=headers).status_code == 403


def test_teacher_sees_only_own_classes():
    classes = by_class(board("teacher", T5))
    assert set(classes) == {"6A"}
    assert classes["6A"]["covered"] == 1 and classes["6A"]["total"] == len(classes["6A"]["points"])


def test_teacher_peer_gaps_are_anonymous():
    c = by_class(board("teacher", T5))["6A"]
    assert "KP02" in c["peer_gaps"] and "KP01" not in c["peer_gaps"]  # 6B covered it, 6A did not; ones 6A already covered do not count
    assert "6B" not in str(c)


def test_head_sees_all_classes_with_details_and_drafts():
    client.post("/api/syllabus", json=example("syllabus"), headers=HEAD)
    result = board("head", HEAD)
    classes = by_class(result)
    assert {"6A", "6B"} <= set(classes) and "points" in classes["6B"]
    assert "peer_gaps" not in classes["6B"]
    assert result["drafts"] and all(d["version"] > result["syllabus"]["version"] for d in result["drafts"])


def test_admin_sees_summaries_invites_and_members():
    result = board("admin", ADMIN)
    classes = by_class(result)
    assert {"6A", "6B"} <= set(classes) and "points" not in classes["6A"]
    assert {i["invite_code"] for i in result["invites"]} == {"DEMO-TEACHER", "DEMO-HEAD", "DEMO-ADMIN"}
    assert "members" in result and "drafts" not in result


def test_alert_when_exam_is_close(monkeypatch):
    monkeypatch.setenv("HUB_EXAM_DATE", "2026-10-17")
    assert by_class(board("teacher", T5))["6A"]["at_risk"] is True


def test_no_alert_when_exam_is_far(monkeypatch):
    monkeypatch.setenv("HUB_EXAM_DATE", "2099-01-01")
    assert by_class(board("teacher", T5))["6A"]["at_risk"] is False


def test_board_shows_syllabus_and_exam_date():
    result = board("teacher", T5)
    assert result["exam_date"] == "2026-12-18"
    assert [kp["kp_id"] for kp in result["syllabus"]["knowledge_points"]] == \
        [p["kp_id"] for p in result["classes"][0]["points"]]
