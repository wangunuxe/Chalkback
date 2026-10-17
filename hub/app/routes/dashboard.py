"""GET /api/dashboard?view=teacher|head|admin（TD6）。

预警规则：剩余未覆盖知识点数 > 距考试剩余周数 × 该班过去平均每周覆盖数 → “考前讲不完”。
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Member, current_member

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(view: Literal["teacher", "head", "admin"], member: Member = Depends(current_member)):
    if view != member.role:
        raise HTTPException(403)
    # TODO(TD6)
    return {"view": view, "classes": [{"class_id": "4A", "covered": 1, "total": 4, "at_risk": False}]}
