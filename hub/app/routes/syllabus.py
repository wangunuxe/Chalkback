"""Syllabus drafts, department head approval, versions (TD3, approval A4). Unapproved versions have no effect."""
import json
import uuid
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from .. import db, syllabus_extract
from ..auth import Member, current_member, require
from ..mock import EXAMPLES

router = APIRouter(prefix="/api/syllabus", tags=["syllabus"])

SCHEMA = Draft202012Validator(json.loads((EXAMPLES.parent / "syllabus.schema.json").read_text(encoding="utf-8")))


def approved(workspace_id: str) -> dict | None:
    with closing(db.connect()) as conn:
        row = conn.execute(
            "SELECT body FROM syllabi WHERE workspace_id = ? AND status = 'approved'"
            " ORDER BY version DESC, approved_at DESC LIMIT 1",
            (workspace_id,),
        ).fetchone()
    return json.loads(row["body"]) if row else None


@router.get("/current")
def current(member: Member = Depends(current_member)):
    syllabus = approved(member.workspace_id)
    if syllabus is None:
        raise HTTPException(404, "no approved syllabus")
    return syllabus


class ExtractRequest(BaseModel):
    filename: str
    content_base64: str
    syllabus_id: str | None = None


@router.post("/extract")
def extract(req: ExtractRequest, member: Member = Depends(require("head"))):
    """AI suggestion from a syllabus file (PDF/DOCX/PPTX/TXT/MD). Saves nothing: the head edits it, then POST /api/syllabus."""
    existing = approved(member.workspace_id)
    syllabus_id = req.syllabus_id or (existing or {}).get("syllabus_id") or "syllabus"
    if existing and existing["syllabus_id"] != syllabus_id:
        existing = None  # a different syllabus: no ids to keep
    try:
        return syllabus_extract.extract(req.filename, req.content_base64, existing, syllabus_id)
    except syllabus_extract.ExtractError as e:
        raise HTTPException(e.status, e.message)


@router.post("")
def create_draft(syllabus: dict, member: Member = Depends(require("head"))):
    # Version number and status are decided by the Hub; values filled in by the uploader are not trusted
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
