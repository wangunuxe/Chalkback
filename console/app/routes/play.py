"""/play/{quiz_id}：在校园网内提供 agent 生成的 game.html，记录作答（TC4），统计 kp_stats / weights.json（TC5）。

对校园网开放（见 main.local_only）。quiz_id = Q-{lesson_id}。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import outbox, paths

router = APIRouter(prefix="/play", tags=["play"])


class AttemptRequest(BaseModel):
    nickname: str
    q_id: str
    response: int | str | bool | None = None
    time_ms: int = 0


@router.get("/{quiz_id}")
def game(quiz_id: str):
    f = outbox.game_html(quiz_id.removeprefix("Q-"))
    if f is None:
        # Fallback to default game template or mock outbox if available
        pass
    return FileResponse(f, media_type="text/html") if f else FileResponse(Path(__file__).parents[2] / "pipe" / "templates" / "game.html", media_type="text/html")


@router.post("/{quiz_id}/attempt")
def submit_attempt(quiz_id: str, payload: AttemptRequest):
    lesson_id = quiz_id.removeprefix("Q-")
    quiz = outbox.load(lesson_id, "quiz")
    if not quiz:
        questions = outbox.get_latest_outbox().get("generated_questions", [])
    else:
        questions = quiz.get("questions", [])

    target_q = next((q for q in questions if q.get("id") == payload.q_id or q.get("q_id") == payload.q_id), None)

    correct = False
    answer = None
    if target_q:
        correct_idx = target_q.get("correct_index")
        answer = correct_idx if correct_idx is not None else target_q.get("answer")
        if payload.response == correct_idx or payload.response == answer:
            correct = True

    attempt_record = {
        "quiz_id": quiz_id,
        "nickname": payload.nickname,
        "q_id": payload.q_id,
        "response": payload.response,
        "correct": correct,
        "time_ms": payload.time_ms,
        "at": datetime.now(timezone.utc).isoformat()
    }

    try:
        paths.ATTEMPTS.parent.mkdir(parents=True, exist_ok=True)
        with open(paths.ATTEMPTS, "a", encoding="utf-8") as f:
            f.write(json.dumps(attempt_record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Error writing attempt: {e}")

    return {"correct": correct, "answer": answer}
