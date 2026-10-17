"""/play/{quiz_id}：在本机提供已发布（A2）的 game.html，记录作答（TC4），统计 kp_stats / weights.json（TC5）。

学生在老师电脑的浏览器里作答，和其它页面一样只允许本机访问。quiz_id = Q-{lesson_id}。
作答接口（H9）：POST /play/{quiz_id}/attempt {nickname, q_id, response, time_ms} → {correct, answer}。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr

from .. import outbox, paths, quizzes, stats
from ..contracts import append_jsonl, now_iso

router = APIRouter(prefix="/play", tags=["play"])


class AttemptRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=40)
    q_id: str
    # 超时为 null（game.html），按答错记录；null 是否写进 attempt 契约待全员确认
    response: StrictBool | StrictInt | StrictStr | None = None
    time_ms: int = Field(default=0, ge=0)


@router.get("/{quiz_id}")
def game(quiz_id: str):
    lesson_id, _ = quizzes.published(quiz_id)
    f = outbox.game_html(lesson_id)
    if f is None:
        raise HTTPException(404, "Game not found")
    return FileResponse(f, media_type="text/html")


@router.post("/{quiz_id}/attempt")
def submit_attempt(quiz_id: str, payload: AttemptRequest):
    lesson_id, quiz = quizzes.published(quiz_id)
    question = next((q for q in quiz["questions"] if q["q_id"] == payload.q_id), None)
    if question is None:
        raise HTTPException(404, f"Question {payload.q_id} not found")

    correct = stats.is_correct(question, payload.response)
    append_jsonl(paths.ATTEMPTS, {
        "quiz_id": quiz_id,
        "nickname": payload.nickname.strip() or "?",
        "q_id": payload.q_id,
        "response": payload.response,
        "correct": correct,
        "time_ms": payload.time_ms,
        "at": now_iso(),
    })
    stats.refresh(lesson_id, quiz)
    return {"correct": correct, "answer": question["answer"]}
