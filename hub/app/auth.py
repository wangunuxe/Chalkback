"""Bearer token → 角色（§6.4）。token 由 POST /api/join 发放，每个 token 对应一个角色。"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass
class Member:
    id: str
    role: str  # teacher | head | admin
    workspace_id: str


def current_member(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Member:
    if cred is None:
        raise HTTPException(401)
    # TODO(TD2): 查 members 表。mock：token 形如 mock-token-<id>，角色看前缀。
    member_id = cred.credentials.removeprefix("mock-token-")
    role = "head" if member_id.startswith("H") else "admin" if member_id.startswith("ADM") else "teacher"
    return Member(id=member_id, role=role, workspace_id="W1")


def require(*roles: str):
    def dep(member: Member = Depends(current_member)) -> Member:
        if member.role not in roles:
            raise HTTPException(403)
        return member
    return dep
