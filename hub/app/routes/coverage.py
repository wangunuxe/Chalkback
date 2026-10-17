"""知识点覆盖表：接收批准的 coverage_share（A3）、撤回（A5）、按班级查询（TD4、TD5）。

入口必须先按 coverage_share schema 校验——这是隐私边界在 Hub 侧的第二道检查。
"""
import json
import uuid
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from jsonschema import Draft202012Validator

from .. import db
from ..auth import Member, current_member, require
from ..mock import EXAMPLES

router = APIRouter(prefix="/api/coverage", tags=["coverage"])

SCHEMA = Draft202012Validator(json.loads((EXAMPLES.parent / "coverage_share.schema.json").read_text(encoding="utf-8")))


def audit(conn, member: Member, action: str, target_id: str, at: str) -> None:
    conn.execute(
        "INSERT INTO audit_events (event_id, workspace_id, actor_role, actor_id, action, target_id, at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (f"EV-{uuid.uuid4().hex[:12]}", member.workspace_id, member.role, member.id, action, target_id, at),
    )


@router.post("")
def share(coverage_share: dict, member: Member = Depends(require("teacher"))):
    errors = [e.message for e in SCHEMA.iter_errors(coverage_share)]
    if errors:
        raise HTTPException(422, errors)
    share_id = f"SH-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(db.connect()) as conn, conn:
        # 同一位老师重传同一节课：新的替换旧的，分钟数不重复计算
        conn.execute(
            "DELETE FROM coverage_shares WHERE teacher_id = ? AND lesson_id = ?",
            (member.id, coverage_share["lesson_id"]),
        )
        conn.execute(
            "INSERT INTO coverage_shares (share_id, workspace_id, teacher_id, lesson_id, class_id, body, shared_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (share_id, member.workspace_id, member.id, coverage_share["lesson_id"], coverage_share["class_id"],
             json.dumps(coverage_share, ensure_ascii=False), now),
        )
        audit(conn, member, "share_coverage", share_id, now)
    return {"share_id": share_id}


@router.delete("/{share_id}", status_code=204)
def revoke(share_id: str, member: Member = Depends(require("teacher"))):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(db.connect()) as conn, conn:
        row = conn.execute(
            "SELECT teacher_id FROM coverage_shares WHERE share_id = ? AND workspace_id = ?",
            (share_id, member.workspace_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404)
        if row["teacher_id"] != member.id:
            raise HTTPException(403, "only the teacher who shared it can revoke")
        conn.execute("DELETE FROM coverage_shares WHERE share_id = ?", (share_id,))
        audit(conn, member, "revoke", share_id, now)
    return Response(status_code=204)


@router.get("")
def by_class(class_id: str, member: Member = Depends(current_member)):
    with closing(db.connect()) as conn:
        # §4：老师只看自己的班（上传过覆盖数据的班）；组长暂时看全校（班级→年级的对应关系待定）
        if member.role == "teacher" and conn.execute(
            "SELECT 1 FROM coverage_shares WHERE workspace_id = ? AND class_id = ? AND teacher_id = ?",
            (member.workspace_id, class_id, member.id),
        ).fetchone() is None:
            raise HTTPException(403, "not your class")
        syllabus = conn.execute(
            "SELECT body FROM syllabi WHERE workspace_id = ? AND status = 'approved'"
            " ORDER BY version DESC, approved_at DESC LIMIT 1",
            (member.workspace_id,),
        ).fetchone()
        if syllabus is None:
            raise HTTPException(404, "no approved syllabus")
        shares = conn.execute(
            "SELECT body FROM coverage_shares WHERE workspace_id = ? AND class_id = ?",
            (member.workspace_id, class_id),
        ).fetchall()

    syllabus = json.loads(syllabus["body"])
    covered = {kp["kp_id"]: False for kp in syllabus["knowledge_points"]}
    minutes = dict.fromkeys(covered, 0.0)
    for row in shares:
        body = json.loads(row["body"])
        if body["syllabus_id"] != syllabus["syllabus_id"]:
            continue
        for point in body["points"]:
            if point["kp_id"] in covered:
                covered[point["kp_id"]] |= point["covered"]
                minutes[point["kp_id"]] += point["minutes"]
    return {"class_id": class_id, "points": [
        {"kp_id": kp_id, "covered": covered[kp_id], "minutes": round(minutes[kp_id], 1)} for kp_id in covered
    ]}
