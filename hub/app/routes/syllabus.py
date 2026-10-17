"""考纲草稿、组长批准、版本（TD3，审批 A4）。未批准的版本不生效。"""
import json
import uuid
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft202012Validator

from .. import db
from ..auth import Member, current_member, require
from ..mock import EXAMPLES

router = APIRouter(prefix="/api/syllabus", tags=["syllabus"])

SCHEMA = Draft202012Validator(json.loads((EXAMPLES.parent / "syllabus.schema.json").read_text(encoding="utf-8")))


@router.get("/current")
def current(member: Member = Depends(current_member)):
    with closing(db.connect()) as conn:
        row = conn.execute(
            "SELECT body FROM syllabi WHERE workspace_id = ? AND status = 'approved'"
            " ORDER BY version DESC, approved_at DESC LIMIT 1",
            (member.workspace_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "no approved syllabus")
    return json.loads(row["body"])


@router.post("")
def create_draft(syllabus: dict, member: Member = Depends(require("head"))):
    # 版本号和状态由 Hub 决定，不信任上传者填写的值
    draft = {**syllabus, "version": 1, "status": "draft"}
    errors = [e.message for e in SCHEMA.iter_errors(draft)]
    if errors:
        raise HTTPException(422, errors)
    with closing(db.connect()) as conn, conn:
        latest = conn.execute(
            "SELECT MAX(version) FROM syllabi WHERE syllabus_id = ?", (draft["syllabus_id"],)
        ).fetchone()[0]
        draft["version"] = (latest or 0) + 1
        conn.execute(
            "INSERT INTO syllabi (workspace_id, syllabus_id, version, status, body) VALUES (?, ?, ?, 'draft', ?)",
            (member.workspace_id, draft["syllabus_id"], draft["version"], json.dumps(draft, ensure_ascii=False)),
        )
    return {"syllabus_id": draft["syllabus_id"], "version": draft["version"]}


@router.post("/{syllabus_id}/approve")
def approve(syllabus_id: str, member: Member = Depends(require("head"))):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(db.connect()) as conn, conn:
        row = conn.execute(
            "SELECT version, body FROM syllabi WHERE workspace_id = ? AND syllabus_id = ? AND status = 'draft'"
            " ORDER BY version DESC LIMIT 1",
            (member.workspace_id, syllabus_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "no draft to approve")
        syllabus = {**json.loads(row["body"]), "status": "approved"}
        conn.execute(
            "UPDATE syllabi SET status = 'approved', body = ?, approved_at = ? WHERE syllabus_id = ? AND version = ?",
            (json.dumps(syllabus, ensure_ascii=False), now, syllabus_id, row["version"]),
        )
        conn.execute(
            "INSERT INTO audit_events (event_id, workspace_id, actor_role, actor_id, action, target_id, at)"
            " VALUES (?, ?, ?, ?, 'approve_syllabus', ?, ?)",
            (f"EV-{uuid.uuid4().hex[:12]}", member.workspace_id, member.role, member.id,
             f"{syllabus_id}@v{row['version']}", now),
        )
    return syllabus
