"""Bearer token -> role (§6.4). Tokens are issued by POST /api/join; each token maps to one role.

Mock tokens for test mode (mock-token-<id>) are off by default: the Hub is deployed on the public internet, and leaving them on would let anyone impersonate an admin.
Local development and the Docker test environment (make hub, docker-compose.yml) explicitly set HUB_MOCK_AUTH=1.
"""
from __future__ import annotations

import os
from contextlib import closing
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db

bearer = HTTPBearer(auto_error=False)


def mock_auth_enabled() -> bool:
    return os.environ.get("HUB_MOCK_AUTH", "0") == "1"


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
    # Mock tokens for test mode (only accepted with HUB_MOCK_AUTH=1): mock-token-<id>, role determined by the prefix.
    if mock_auth_enabled() and cred.credentials.startswith("mock-token-"):
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
