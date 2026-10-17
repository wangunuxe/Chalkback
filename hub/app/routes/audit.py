"""GET /api/audit（TD5、TD6）：按角色过滤——老师看自己的，组长看本年级，管理员看全部（不含内容本身）。"""
from contextlib import closing

from fastapi import APIRouter, Depends

from .. import db
from ..auth import Member, current_member

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def audit(member: Member = Depends(current_member)):
    query = "SELECT * FROM audit_events WHERE workspace_id = ?"
    params = [member.workspace_id]
    # 组长暂时看全校记录：班级→年级的对应关系待定
    if member.role == "teacher":
        query += " AND actor_id = ?"
        params.append(member.id)
    with closing(db.connect()) as conn:
        rows = conn.execute(query + " ORDER BY at, rowid", params).fetchall()
    return [
        {"event_id": r["event_id"], "workspace_id": r["workspace_id"],
         "actor": {"role": r["actor_role"], "id": r["actor_id"]},
         "action": r["action"], "target_id": r["target_id"], "at": r["at"]}
        for r in rows
    ]
