"""POST /api/join（TD2）。"""
from pydantic import BaseModel
from typing import Literal

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["join"])


class JoinRequest(BaseModel):
    invite_code: str
    display_name: str
    role: Literal["teacher", "head", "admin"]


@router.post("/join")
def join(req: JoinRequest):
    # TODO(TD2): 校验邀请码，建成员，发 token，写 audit_event(join)
    return {"teacher_id": "T1", "token": "mock-token-T1", "workspace_id": "W1"}
