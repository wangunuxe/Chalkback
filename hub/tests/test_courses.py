"""Courses: classes -> courses -> knowledge points; a teacher sends a course summary to the department head and can withdraw it."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.main import app
from app.mock import example

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)
T7 = {"Authorization": "Bearer mock-token-T7"}
T8 = {"Authorization": "Bearer mock-token-T8"}
HEAD = {"Authorization": "Bearer mock-token-H1"}
ADMIN = {"Authorization": "Bearer mock-token-ADM1"}
AUDIT = Draft202012Validator(json.loads((ROOT / "contracts" / "audit_event.schema.json").read_text(encoding="utf-8")))
SYLLABUS = example("syllabus")["syllabus_id"]
SUMMARY = "Over 3 lessons, 3B worked on the passé composé with avoir. Next: the agreement of the past participle."


def create(headers=T7, **fields):
    body = {"name": "Grammaire 3B", "class_id": "3B", "syllabus_id": SYLLABUS, **fields}
    r = client.post("/api/courses", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def visible(headers):
    return {c["course_id"]: c for c in client.get("/api/courses", headers=headers).json()}


def send(course_id, text=SUMMARY, headers=T7):
    return client.put(f"/api/courses/{course_id}/summary", json={"text": text}, headers=headers)


def share(teacher, headers, class_id, day, points, syllabus_id=SYLLABUS):
    body = {**example("coverage_share"), "class_id": class_id, "lesson_id": f"L-{teacher}-{day}-0900",
            "date": f"{day[:4]}-{day[4:6]}-{day[6:]}", "syllabus_id": syllabus_id,
            "points": [{"kp_id": k, "covered": True, "minutes": 5} for k in points]}
    assert client.post("/api/coverage", json=body, headers=headers).status_code == 200


def test_summary_reaches_the_head_only_when_sent():
    course = create(class_id="3A", description="Le passé composé, trimestre 1")
    cid = course["course_id"]
    assert course["summary"] is None and course["teacher"]["id"] == "T7"
    assert visible(HEAD)[cid]["summary"] is None      # the head sees the course and its progress, but no summary yet
    assert cid not in visible(T8)                     # other teachers never see it

    sent = send(cid).json()
    assert sent["summary"]["text"] == SUMMARY and sent["summary"]["sent_at"]
    assert visible(HEAD)[cid]["summary"]["text"] == SUMMARY

    send(cid, "Updated summary")                      # sending again replaces it
    assert visible(HEAD)[cid]["summary"]["text"] == "Updated summary"

    assert client.delete(f"/api/courses/{cid}/summary", headers=T7).json()["summary"] is None
    assert visible(HEAD)[cid]["summary"] is None


def test_admin_sees_progress_only():
    cid = create(class_id="3C")["course_id"]
    send(cid)
    course = visible(ADMIN)[cid]
    assert "summary" not in course and "points" not in course
    assert course["progress"]["total"] == len(example("syllabus")["knowledge_points"])


def test_head_sees_knowledge_points_of_each_course():
    cid = create(headers=T8, class_id="3D")["course_id"]
    share("T8", T8, "3D", "20261010", ["KP01"])
    share("T7", T7, "3D", "20261011", ["KP02"])      # another teacher teaching the same class does not count for T8's course
    course = visible(HEAD)[cid]
    covered = {p["kp_id"]: p for p in course["points"] if p["covered"]}
    assert list(covered) == ["KP01"] and covered["KP01"]["minutes"] == 5 and covered["KP01"]["title"]
    assert course["progress"]["covered"] == 1
    assert course["lessons"] == {"count": 1, "first": "2026-10-10", "last": "2026-10-10"}


def test_only_the_teacher_changes_their_course():
    cid = create(class_id="3E")["course_id"]
    assert send(cid, headers=T8).status_code == 403
    assert client.delete(f"/api/courses/{cid}/summary", headers=T8).status_code == 403
    for role in (HEAD, ADMIN):
        assert send(cid, headers=role).status_code == 403
        assert client.post("/api/courses", json={"name": "x", "class_id": "x", "syllabus_id": SYLLABUS}, headers=role).status_code == 403
    assert send("C-nope").status_code == 404


def test_summary_must_not_be_empty_or_huge():
    cid = create(class_id="3F")["course_id"]
    assert send(cid, "   ").status_code == 422
    assert send(cid, "x" * 3001).status_code == 422


def test_one_course_per_teacher_class_and_syllabus():
    create(class_id="3G")
    r = client.post("/api/courses", json={"name": "Again", "class_id": "3G", "syllabus_id": SYLLABUS}, headers=T7)
    assert r.status_code == 409
    create(headers=T8, class_id="3G")                 # another teacher can teach the same class


def test_course_needs_an_approved_syllabus():
    r = client.post("/api/courses", json={"name": "Maths", "class_id": "3B", "syllabus_id": "maths-4e"}, headers=T7)
    assert r.status_code == 422


def test_course_with_a_summary_cannot_be_deleted_until_withdrawn():
    cid = create(class_id="3H")["course_id"]
    send(cid)
    assert client.delete(f"/api/courses/{cid}", headers=T7).status_code == 409
    client.delete(f"/api/courses/{cid}/summary", headers=T7)
    assert client.delete(f"/api/courses/{cid}", headers=T7).status_code == 204
    assert cid not in visible(T7)


def test_send_and_withdraw_are_audited():
    cid = create(class_id="3J")["course_id"]
    send(cid)
    for _ in range(2):  # withdrawing twice writes one entry
        client.delete(f"/api/courses/{cid}/summary", headers=T7)
    events = [e for e in client.get("/api/audit", headers=HEAD).json() if e["target_id"] == cid]
    assert [e["action"] for e in events] == ["share_summary", "withdraw_summary"]
    for e in events:
        AUDIT.validate(e)


def test_second_subject_does_not_replace_the_main_syllabus():
    maths = {"syllabus_id": "maths-3e", "version": 1, "status": "draft", "subject": "maths", "level": "3e",
             "knowledge_points": [{"kp_id": "M01", "title": "Les fractions", "keywords": ["fraction"]}]}
    assert client.post("/api/syllabus", json=maths, headers=HEAD).status_code == 200
    assert client.post("/api/syllabus/maths-3e/approve", headers=HEAD).status_code == 200
    assert client.get("/api/syllabus/current", headers=T7).json()["syllabus_id"] == SYLLABUS
    assert client.get("/api/syllabus/current?syllabus_id=maths-3e", headers=T7).json()["subject"] == "maths"
    assert {s["syllabus_id"] for s in client.get("/api/syllabus", headers=T7).json()} >= {SYLLABUS, "maths-3e"}

    # maths lessons count for the maths course, not for the French board
    cid = create(name="Maths 3K", class_id="3K", syllabus_id="maths-3e")["course_id"]
    share("T7", T7, "3K", "20261012", ["M01"], syllabus_id="maths-3e")
    assert visible(HEAD)[cid]["progress"] == {"covered": 1, "total": 1}
    board = client.get("/api/dashboard?view=head", headers=HEAD).json()
    assert board["syllabus"]["syllabus_id"] == SYLLABUS and "3K" not in {c["class_id"] for c in board["classes"]}


def test_prototype_courses_table_is_kept_aside(tmp_path):
    import sqlite3

    from app import db
    conn = sqlite3.connect(tmp_path / "old.db")
    conn.execute("CREATE TABLE courses (course_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
    conn.execute("INSERT INTO courses VALUES ('C-old', 'sent')")
    db.upgrade_prototype_courses(conn)
    conn.executescript(db.SCHEMA)
    assert conn.execute("SELECT course_id FROM courses_prototype").fetchall() == [("C-old",)]
    assert "summary" in {r[1] for r in conn.execute("PRAGMA table_info(courses)")}
    db.upgrade_prototype_courses(conn)  # a second start changes nothing
