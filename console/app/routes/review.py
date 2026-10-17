"""/review：列出 outbox、漏讲提醒、逐题审核（A2）、出处、批准共享覆盖数据（A3）（TC3）。

- 每个审核动作追加一条 edit_event 到 state/edits.jsonl。
- 批准共享时用 share.to_coverage_share() 生成上传内容，先用 coverage_share schema 校验再发。
"""
from fastapi import APIRouter, HTTPException

from .. import outbox

router = APIRouter(prefix="/review", tags=["review"])


@router.get("")
def list_lessons():
    return {"lessons": outbox.ready_lessons()}


@router.get("/{lesson_id}")
def lesson_detail(lesson_id: str):
    quiz = outbox.load(lesson_id, "quiz")
    if quiz is None:
        raise HTTPException(404, "outbox not ready")
    return {"quiz": quiz, "alerts": outbox.load(lesson_id, "alerts"), "coverage": outbox.load(lesson_id, "coverage")}

# TODO(TC3): POST 审核动作（approve/edit/delete/reject）、GET 出处截图、POST 批准共享
