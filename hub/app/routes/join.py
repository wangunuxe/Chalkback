"""POST /api/join（TD2）。"""
import re
import secrets
import sqlite3
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


def next_member_id(conn, role: str) -> str:
    """前缀 + 已有最大编号 + 1（不用 COUNT：编号不连续时 COUNT 会撞上已有的编号）。"""
    prefix = ID_PREFIX[role]
    numbers = [int(m.group(1)) for (mid,) in conn.execute("SELECT member_id FROM members WHERE role = ?", (role,))
               if (m := re.fullmatch(rf"{prefix}(\d+)", mid))]
    return f"{prefix}{max(numbers, default=0) + 1}"


def insert_member(conn, workspace_id: str, req: "JoinRequest", token: str, attempts: int = 5) -> str:
    """两个人同时加入可能算出同一个编号：撞了就重算，而不是返回 500。"""
    for _ in range(attempts):
        member_id = next_member_id(conn, req.role)
        try:
            conn.execute(
                "INSERT INTO members (member_id, workspace_id, display_name, role, token) VALUES (?, ?, ?, ?, ?)",
                (member_id, workspace_id, req.display_name, req.role, token),
            )
            return member_id
        except sqlite3.IntegrityError:
            continue
    raise HTTPException(503, "too many people joining at once, please try again")


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
        token = secrets.token_urlsafe(24)
        member_id = insert_member(conn, workspace_id, req, token)
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
