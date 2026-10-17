"""GET /api/audit (TD5, TD6): filtered by role -- teachers see their own, department heads see their grade, admins see everything (without the content itself)."""
from contextlib import closing

from fastapi import APIRouter, Depends

from .. import db
from ..auth import Member, current_member

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def audit(member: Member = Depends(current_member)):
    query = "SELECT * FROM audit_events WHERE workspace_id = ?"
    params = [member.workspace_id]
    # A department head sees the whole school's records for now: class -> grade mapping TBD
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
