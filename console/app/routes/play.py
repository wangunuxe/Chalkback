"""/play/{quiz_id}: serve the published (A2) game.html locally, record attempts (TC4), compute kp_stats / weights.json (TC5).

Students answer in the browser on the teacher's computer; like every other page, it is local-only. quiz_id = Q-{lesson_id}.
Answer endpoint (H9): POST /play/{quiz_id}/attempt {nickname, q_id, response, time_ms} -> {correct, answer}.
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
    # A timeout is null (game.html) and is recorded as wrong; whether null goes into the attempt contract still needs team-wide confirmation
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
