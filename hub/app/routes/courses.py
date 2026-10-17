"""Courses: what a teacher teaches to a class (a group of students) from one syllabus, and the summary they send to the department head.

Classes -> courses -> knowledge points: a course's progress is computed from the coverage the teacher already shared
(coverage_shares) for its class and syllabus, so one course per teacher, class and syllabus.
The summary text is generated on the teacher's computer (by the screenpipe pipe) and reaches the Hub only when the teacher
sends it; the teacher can withdraw it. Each send and withdrawal is audited.

Who sees what (§4): teachers see their own courses; department heads see every course with knowledge point detail and the
summaries that were sent; admins see every course's progress only (no knowledge point detail, no summaries).
"""
from __future__ import annotations

import json
import uuid
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from .. import db
from ..auth import Member, current_member, require
from .coverage import audit, class_points, current_syllabus

router = APIRouter(prefix="/api/courses", tags=["courses"])

MAX_COURSES = 100        # per teacher
MAX_SUMMARY = 3000       # characters


class CourseIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # strip before the length checks, so "  " counts as empty

    name: str = Field(min_length=1, max_length=80)
    class_id: str = Field(min_length=1, max_length=20)
    syllabus_id: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class SummaryIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=MAX_SUMMARY)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def own_course(conn, course_id: str, member: Member):
    row = conn.execute(
        "SELECT * FROM courses WHERE course_id = ? AND workspace_id = ?", (course_id, member.workspace_id)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "no such course")
    if row["teacher_id"] != member.id:
        raise HTTPException(403, "only the teacher of this course can change it")
    return row


def course_json(conn, row, role: str) -> dict:
    ws, teacher_id = row["workspace_id"], row["teacher_id"]
    syllabus = current_syllabus(conn, ws, row["syllabus_id"])
    titles = {kp["kp_id"]: kp["title"] for kp in syllabus["knowledge_points"]} if syllabus else {}
    points = class_points(conn, ws, row["class_id"], syllabus, teacher_id=teacher_id) if syllabus else []
    lessons = conn.execute(
        "SELECT COUNT(*) AS n, MIN(json_extract(body, '$.date')) AS first, MAX(json_extract(body, '$.date')) AS last"
        " FROM coverage_shares WHERE workspace_id = ? AND teacher_id = ? AND class_id = ? AND json_extract(body, '$.syllabus_id') = ?",
        (ws, teacher_id, row["class_id"], row["syllabus_id"]),
    ).fetchone()
    teacher = conn.execute("SELECT display_name FROM members WHERE member_id = ?", (teacher_id,)).fetchone()
    result = {
        "course_id": row["course_id"], "name": row["name"], "class_id": row["class_id"], "description": row["description"],
        "created_at": row["created_at"],
        "teacher": {"id": teacher_id, "name": teacher["display_name"] if teacher else None},
        "syllabus": {"syllabus_id": row["syllabus_id"], "subject": syllabus["subject"] if syllabus else row["syllabus_id"],
                     "level": syllabus["level"] if syllabus else ""},
        "progress": {"covered": sum(p["covered"] for p in points), "total": len(points)},
        "lessons": {"count": lessons["n"], "first": lessons["first"], "last": lessons["last"]},
    }
    if role in ("teacher", "head"):
        result["points"] = [{**p, "title": titles.get(p["kp_id"], p["kp_id"])} for p in points]
        result["summary"] = None if row["summary"] is None else {"text": row["summary"], "sent_at": row["summary_sent_at"]}
    return result


@router.get("")
def list_courses(member: Member = Depends(current_member)):
    """Teachers: their own courses. Department heads and admins: every course in the school, by class."""
    with closing(db.connect()) as conn:
        query = "SELECT * FROM courses WHERE workspace_id = ?"
        params = [member.workspace_id]
        if member.role == "teacher":
            query += " AND teacher_id = ?"
            params.append(member.id)
        rows = conn.execute(query + " ORDER BY class_id, name, rowid", params).fetchall()
        return [course_json(conn, r, member.role) for r in rows]


@router.post("")
def create_course(course: CourseIn, member: Member = Depends(require("teacher"))):
    with closing(db.connect()) as conn, conn:
        if current_syllabus(conn, member.workspace_id, course.syllabus_id) is None:
            raise HTTPException(422, f"syllabus {course.syllabus_id} has no approved version")
        if conn.execute(
            "SELECT 1 FROM courses WHERE workspace_id = ? AND teacher_id = ? AND class_id = ? AND syllabus_id = ?",
            (member.workspace_id, member.id, course.class_id, course.syllabus_id),
        ).fetchone():
            raise HTTPException(409, f"you already have a course for class {course.class_id} with this syllabus")
        count = conn.execute("SELECT COUNT(*) FROM courses WHERE teacher_id = ? AND workspace_id = ?",
                             (member.id, member.workspace_id)).fetchone()[0]
        if count >= MAX_COURSES:
            raise HTTPException(409, f"at most {MAX_COURSES} courses per teacher")
        course_id = f"C-{uuid.uuid4().hex[:10]}"
        conn.execute(
            "INSERT INTO courses (course_id, workspace_id, teacher_id, name, class_id, syllabus_id, description, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (course_id, member.workspace_id, member.id, course.name, course.class_id, course.syllabus_id,
             course.description, now()),
        )
        return course_json(conn, own_course(conn, course_id, member), member.role)


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str, member: Member = Depends(require("teacher"))):
    with closing(db.connect()) as conn, conn:
        if own_course(conn, course_id, member)["summary"] is not None:
            raise HTTPException(409, "withdraw the summary you sent before deleting the course")
        conn.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    return Response(status_code=204)


@router.put("/{course_id}/summary")
def send_summary(course_id: str, summary: SummaryIn, member: Member = Depends(require("teacher"))):
    """Send (or replace) the course summary for the department head: the teacher's approval to share this text."""
    with closing(db.connect()) as conn, conn:
        row = own_course(conn, course_id, member)
        at = now()
        conn.execute("UPDATE courses SET summary = ?, summary_sent_at = ? WHERE course_id = ?", (summary.text, at, course_id))
        audit(conn, member, "share_summary", row["course_id"], at)
        return course_json(conn, own_course(conn, course_id, member), member.role)


@router.delete("/{course_id}/summary")
def withdraw_summary(course_id: str, member: Member = Depends(require("teacher"))):
    with closing(db.connect()) as conn, conn:
        row = own_course(conn, course_id, member)
        if row["summary"] is not None:
            conn.execute("UPDATE courses SET summary = NULL, summary_sent_at = NULL WHERE course_id = ?", (course_id,))
            audit(conn, member, "withdraw_summary", course_id, now())
        return course_json(conn, own_course(conn, course_id, member), member.role)
