"""POST /api/join（TD2）。"""
import secrets
import uuid
from contextlib import closing
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db

router = APIRouter(prefix="/api", tags=["join"])

# 成员编号前缀，和 mock token 的规则一致（auth.py）
ID_PREFIX = {"teacher": "T", "head": "H", "admin": "ADM"}


class JoinRequest(BaseModel):
    invite_code: str
    display_name: str
    role: Literal["teacher", "head", "admin"]


@router.post("/join")
def join(req: JoinRequest):
    with closing(db.connect()) as conn, conn:
        invite = conn.execute(
            "SELECT workspace_id, role FROM invites WHERE invite_code = ?", (req.invite_code,)
        ).fetchone()
        if invite is None:
            raise HTTPException(404, "unknown invite code")
        if invite["role"] != req.role:
            raise HTTPException(403, "invite code is not for this role")

        workspace_id = invite["workspace_id"]
        count = conn.execute("SELECT COUNT(*) FROM members WHERE role = ?", (req.role,)).fetchone()[0]
        member_id = f"{ID_PREFIX[req.role]}{count + 1}"
        token = secrets.token_urlsafe(24)
        conn.execute(
            "INSERT INTO members (member_id, workspace_id, display_name, role, token) VALUES (?, ?, ?, ?, ?)",
            (member_id, workspace_id, req.display_name, req.role, token),
        )
        conn.execute(
            "INSERT INTO audit_events (event_id, workspace_id, actor_role, actor_id, action, target_id, at)"
            " VALUES (?, ?, ?, ?, 'join', ?, ?)",
            (
                f"EV-{uuid.uuid4().hex[:12]}",
                workspace_id,
                req.role,
                member_id,
                workspace_id,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    return {"teacher_id": member_id, "token": token, "workspace_id": workspace_id}
