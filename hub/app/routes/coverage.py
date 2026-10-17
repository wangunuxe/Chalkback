"""知识点覆盖表：接收批准的 coverage_share（A3）、撤回（A5）、按班级查询（TD4、TD5）。

入口必须先按 coverage_share schema 校验——这是隐私边界在 Hub 侧的第二道检查。
"""
from fastapi import APIRouter, Depends, Response

from ..auth import current_member, require

router = APIRouter(prefix="/api/coverage", tags=["coverage"])


@router.post("")
def share(coverage_share: dict, _=Depends(require("teacher"))):
    # TODO(TD5): schema 校验（失败 422）、入库、写 audit_event(share_coverage)
    return {"share_id": "SH-0001"}


@router.delete("/{share_id}", status_code=204)
def revoke(share_id: str, _=Depends(require("teacher"))):
    # TODO(TD5): 只允许本人撤回；删除并写 audit_event(revoke)
    return Response(status_code=204)


@router.get("")
def by_class(class_id: str, _=Depends(current_member)):
    # TODO(TD4): 按 §4 权限表过滤；该班已讲 / 未讲的知识点及时长
    return {"class_id": class_id, "points": [
        {"kp_id": "KP01", "covered": False, "minutes": 0},
        {"kp_id": "KP02", "covered": False, "minutes": 0},
        {"kp_id": "KP03", "covered": True, "minutes": 4.5},
        {"kp_id": "KP04", "covered": False, "minutes": 0},
    ]}
