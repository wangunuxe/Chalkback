"""Knowledge point coverage table: receive approved coverage_share (A3), withdraw (A5), query by class (TD4, TD5).

Input must first be validated against the coverage_share schema -- this is the Hub-side second check of the privacy boundary.
Then the content is checked: the teacher in lesson_id must be the uploader; the syllabus version must be an approved version in this workspace; the knowledge points must be in that version.
"""
import json
import uuid
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from jsonschema import Draft202012Validator

from .. import db
from ..auth import Member, current_member, require
from ..mock import EXAMPLES

router = APIRouter(prefix="/api/coverage", tags=["coverage"])

SCHEMA = Draft202012Validator(json.loads((EXAMPLES.parent / "coverage_share.schema.json").read_text(encoding="utf-8")))


def audit(conn, member: Member, action: str, target_id: str, at: str) -> None:
    conn.execute(
        "INSERT INTO audit_events (event_id, workspace_id, actor_role, actor_id, action, target_id, at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (f"EV-{uuid.uuid4().hex[:12]}", member.workspace_id, member.role, member.id, action, target_id, at),
    )


def approved_syllabus(conn, workspace_id: str, syllabus_id: str, version: int) -> dict | None:
    row = conn.execute(
        "SELECT body FROM syllabi WHERE workspace_id = ? AND syllabus_id = ? AND version = ? AND status = 'approved'",
        (workspace_id, syllabus_id, version),
    ).fetchone()
    return None if row is None else json.loads(row["body"])


def content_errors(conn, coverage_share: dict, member: Member) -> list[str]:
    errors = []
    lesson_teacher = coverage_share["lesson_id"].split("-")[1]  # L-{teacher_id}-{YYYYMMDD}-{HHMM}
    if lesson_teacher != member.id:
        errors.append(f"lesson {coverage_share['lesson_id']} belongs to {lesson_teacher}, not to you ({member.id})")
    syllabus = approved_syllabus(conn, member.workspace_id, coverage_share["syllabus_id"], coverage_share["syllabus_version"])
    if syllabus is None:
        errors.append(f"syllabus {coverage_share['syllabus_id']} v{coverage_share['syllabus_version']} is not an approved version")
    else:
        known = {kp["kp_id"] for kp in syllabus["knowledge_points"]}
        unknown = sorted({p["kp_id"] for p in coverage_share["points"]} - known)
        if unknown:
            errors.append(f"knowledge points not in this syllabus version: {unknown}")
    return errors


@router.post("")
def share(coverage_share: dict, member: Member = Depends(require("teacher"))):
    errors = [e.message for e in SCHEMA.iter_errors(coverage_share)]
    if errors:
        raise HTTPException(422, errors)
    share_id = f"SH-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(db.connect()) as conn, conn:
        errors = content_errors(conn, coverage_share, member)
        if errors:
            raise HTTPException(422, errors)
        # Same teacher re-uploads the same lesson: the new one replaces the old one, so minutes are not counted twice
        conn.execute(
            "DELETE FROM coverage_shares WHERE teacher_id = ? AND lesson_id = ?",
            (member.id, coverage_share["lesson_id"]),
        )
        conn.execute(
            "INSERT INTO coverage_shares (share_id, workspace_id, teacher_id, lesson_id, class_id, body, shared_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (share_id, member.workspace_id, member.id, coverage_share["lesson_id"], coverage_share["class_id"],
             json.dumps(coverage_share, ensure_ascii=False), now),
        )
        audit(conn, member, "share_coverage", share_id, now)
    return {"share_id": share_id}


@router.delete("/{share_id}", status_code=204)
def revoke(share_id: str, member: Member = Depends(require("teacher"))):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(db.connect()) as conn, conn:
        row = conn.execute(
            "SELECT teacher_id FROM coverage_shares WHERE share_id = ? AND workspace_id = ?",
            (share_id, member.workspace_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404)
        if row["teacher_id"] != member.id:
            raise HTTPException(403, "only the teacher who shared it can revoke")
        conn.execute("DELETE FROM coverage_shares WHERE share_id = ?", (share_id,))
        audit(conn, member, "revoke", share_id, now)
    return Response(status_code=204)


def current_syllabus(conn, workspace_id: str) -> dict | None:
    row = conn.execute(
        "SELECT body FROM syllabi WHERE workspace_id = ? AND status = 'approved'"
        " ORDER BY version DESC, approved_at DESC LIMIT 1",
        (workspace_id,),
    ).fetchone()
    return None if row is None else json.loads(row["body"])


def class_points(conn, workspace_id: str, class_id: str, syllabus: dict) -> list[dict]:
    """List every knowledge point of the syllabus: covered means "taught in any lesson", minutes are summed."""
    covered = {kp["kp_id"]: False for kp in syllabus["knowledge_points"]}
    minutes = dict.fromkeys(covered, 0.0)
    for row in conn.execute(
        "SELECT body FROM coverage_shares WHERE workspace_id = ? AND class_id = ?", (workspace_id, class_id)
    ):
        body = json.loads(row["body"])
        if body["syllabus_id"] != syllabus["syllabus_id"]:
            continue
        for point in body["points"]:
            if point["kp_id"] in covered:
                covered[point["kp_id"]] |= point["covered"]
                minutes[point["kp_id"]] += point["minutes"]
    return [{"kp_id": kp_id, "covered": covered[kp_id], "minutes": round(minutes[kp_id], 1)} for kp_id in covered]


@router.get("")
def by_class(class_id: str, member: Member = Depends(current_member)):
    with closing(db.connect()) as conn:
        # §4: a teacher only sees their own classes (classes they uploaded coverage for); a department head sees the whole school for now (class -> grade mapping TBD)
        if member.role == "teacher" and conn.execute(
            "SELECT 1 FROM coverage_shares WHERE workspace_id = ? AND class_id = ? AND teacher_id = ?",
            (member.workspace_id, class_id, member.id),
        ).fetchone() is None:
            raise HTTPException(403, "not your class")
        syllabus = current_syllabus(conn, member.workspace_id)
        if syllabus is None:
            raise HTTPException(404, "no approved syllabus")
        return {"class_id": class_id, "points": class_points(conn, member.workspace_id, class_id, syllabus)}
