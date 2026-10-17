"""Bearer token → 角色（§6.4）。token 由 POST /api/join 发放，每个 token 对应一个角色。"""
from __future__ import annotations

import os
from contextlib import closing
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db

bearer = HTTPBearer(auto_error=False)


@dataclass
class Member:
    id: str
    role: str  # teacher | head | admin
    workspace_id: str


def current_member(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Member:
    if cred is None:
        raise HTTPException(401)
    with closing(db.connect()) as conn:
        row = conn.execute(
            "SELECT member_id, role, workspace_id FROM members WHERE token = ?", (cred.credentials,)
        ).fetchone()
    if row is not None:
        return Member(id=row["member_id"], role=row["role"], workspace_id=row["workspace_id"])
    # 联调期保留 mock token（HUB_MOCK_AUTH=0 关闭）：形如 mock-token-<id>，角色看前缀。
    if os.environ.get("HUB_MOCK_AUTH", "1") != "0" and cred.credentials.startswith("mock-token-"):
        member_id = cred.credentials.removeprefix("mock-token-")
        role = "head" if member_id.startswith("H") else "admin" if member_id.startswith("ADM") else "teacher"
        return Member(id=member_id, role=role, workspace_id="W1")
    raise HTTPException(401)


def require(*roles: str):
    def dep(member: Member = Depends(current_member)) -> Member:
        if member.role not in roles:
            raise HTTPException(403)
        return member
    return dep
