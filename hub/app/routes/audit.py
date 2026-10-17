"""GET /api/audit（TD5、TD6）：按角色过滤——老师看自己的，组长看本年级，管理员看全部（不含内容本身）。"""
from fastapi import APIRouter, Depends

from ..auth import current_member
from ..mock import example

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def audit(_=Depends(current_member)):
    # TODO(TD5)
    return [example("audit_event")]
