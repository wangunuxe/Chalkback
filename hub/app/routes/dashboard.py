"""GET /api/dashboard?view=teacher|head|admin (TD6).

Alert rule: remaining uncovered knowledge points > weeks left until the exam x the class's average coverage per week so far -> "won't finish before the exam".

Each view follows the §4 permission table: teachers only see their own classes;
department heads see per-class knowledge point details and syllabus drafts awaiting approval (class -> grade mapping TBD, whole school for now);
admins only see per-class summaries, plus invite codes and member counts.
The board shows one syllabus (subject): the school's main one, or another approved one with ?syllabus_id= (the head's subject picker).
"""
import os
from contextlib import closing
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..auth import Member, current_member
from .coverage import class_points, current_syllabus

router = APIRouter(prefix="/api", tags=["dashboard"])


def class_summary(conn, workspace_id: str, class_id: str, syllabus: dict, weeks_left: float | None, today: date):
    points = class_points(conn, workspace_id, class_id, syllabus)
    covered = sum(p["covered"] for p in points)
    first = conn.execute(
        "SELECT MIN(json_extract(body, '$.date')) FROM coverage_shares WHERE workspace_id = ? AND class_id = ?"
        " AND json_extract(body, '$.syllabus_id') = ?",
        (workspace_id, class_id, syllabus["syllabus_id"]),
    ).fetchone()[0]
    weeks_taught = max(1.0, (today - date.fromisoformat(first)).days / 7) if first else 1.0
    rate = covered / weeks_taught
    at_risk = weeks_left is not None and len(points) - covered > weeks_left * rate
    return {"class_id": class_id, "covered": covered, "total": len(points),
            "weekly_rate": round(rate, 2), "at_risk": at_risk, "points": points}


@router.get("/dashboard")
def dashboard(view: Literal["teacher", "head", "admin"], syllabus_id: str | None = None,
              member: Member = Depends(current_member)):
    if view != member.role:
        raise HTTPException(403)
    ws = member.workspace_id
    today = date.today()
    with closing(db.connect()) as conn:
        # A new school has no approved syllabus yet: the board is empty until the department head publishes one
        syllabus = current_syllabus(conn, ws, syllabus_id)
        if syllabus is None and syllabus_id is not None:
            raise HTTPException(404, f"syllabus {syllabus_id} has no approved version")
        workspace = conn.execute("SELECT name, exam_date FROM workspaces WHERE workspace_id = ?", (ws,)).fetchone()
        exam_date = os.environ.get("HUB_EXAM_DATE") or (workspace["exam_date"] if workspace else None)
        weeks_left = max(0.0, (date.fromisoformat(exam_date) - today).days / 7) if exam_date else None

        # Only lessons of the board's syllabus; other subjects show up per course (GET /api/courses)
        of_syllabus = " AND json_extract(body, '$.syllabus_id') = ?"
        all_classes = [] if syllabus is None else [r[0] for r in conn.execute(
            "SELECT DISTINCT class_id FROM coverage_shares WHERE workspace_id = ?" + of_syllabus + " ORDER BY class_id",
            (ws, syllabus["syllabus_id"]))]
        if view == "teacher" and syllabus is not None:
            mine = {r[0] for r in conn.execute(
                "SELECT DISTINCT class_id FROM coverage_shares WHERE workspace_id = ? AND teacher_id = ?" + of_syllabus,
                (ws, member.id, syllabus["syllabus_id"]))}
            shown = [c for c in all_classes if c in mine]
        else:
            shown = all_classes
        classes = [class_summary(conn, ws, c, syllabus, weeks_left, today) for c in shown]

        result = {
            "view": view,
            "workspace": {"workspace_id": ws, "name": workspace["name"] if workspace else ws},
            "exam_date": exam_date,
            "weeks_left": None if weeks_left is None else round(weeks_left, 1),
            "syllabus": None if syllabus is None else {
                "syllabus_id": syllabus["syllabus_id"], "version": syllabus["version"],
                "subject": syllabus["subject"], "level": syllabus["level"],
                "knowledge_points": [{"kp_id": kp["kp_id"], "title": kp["title"]} for kp in syllabus["knowledge_points"]]},
            "classes": classes,
        }

        if view == "head":
            # Drafts newer than the latest approved version of their own syllabus (one syllabus per subject)
            result["drafts"] = [dict(r) for r in conn.execute(
                "SELECT s.syllabus_id, s.version FROM syllabi s WHERE s.workspace_id = ? AND s.status = 'draft'"
                " AND s.version > COALESCE((SELECT MAX(a.version) FROM syllabi a WHERE a.workspace_id = s.workspace_id"
                " AND a.syllabus_id = s.syllabus_id AND a.status = 'approved'), 0)"
                " ORDER BY s.syllabus_id, s.version", (ws,))]
        elif view == "admin":
            for c in classes:
                del c["points"]
            result["invites"] = [dict(r) for r in conn.execute(
                "SELECT invite_code, role FROM invites WHERE workspace_id = ? ORDER BY role", (ws,))]
            result["members"] = {r["role"]: r["n"] for r in conn.execute(
                "SELECT role, COUNT(*) AS n FROM members WHERE workspace_id = ? GROUP BY role", (ws,))}
    return result
