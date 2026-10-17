"""/play/{quiz_id}：在校园网内提供 agent 生成的 game.html，记录作答（TC4），统计 kp_stats / weights.json（TC5）。

对校园网开放（见 main.local_only）。quiz_id = Q-{lesson_id}。
TODO(B+C): 作答提交接口技术文档未定义，H9 前约定；下面的 POST 路径是占位。
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import outbox

router = APIRouter(prefix="/play", tags=["play"])


@router.get("/{quiz_id}")
def game(quiz_id: str):
    f = outbox.game_html(quiz_id.removeprefix("Q-"))
    if f is None:
        raise HTTPException(404)
    # TODO(TC4): 只提供 status=published 的测验
    return FileResponse(f, media_type="text/html")


@router.post("/{quiz_id}/attempt")
def submit_attempt(quiz_id: str):
    # TODO(TC4): 校验 attempt 契约，追加到 state/attempts.jsonl
    raise HTTPException(501)
