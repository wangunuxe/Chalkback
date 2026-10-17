"""Quiz review (A2, TC3): approve / edit / delete / reject each question, then publish or reject the whole quiz.

- Every action rewrites quiz.json in the outbox (the whole file is re-validated against the quiz schema) and appends an edit_event to state/edits.jsonl;
  pipe step 6 uses these to learn the teacher's style (`pipe/scripts/style_inputs.py`).
- Only quizzes with status = published are served under /play; publishing regenerates game.html with pipe's build_game,
  so students see the reviewed questions, and the page contains neither the answers nor the teacher's verbatim words from class.
"""
from __future__ import annotations

import re

from fastapi import HTTPException

from . import outbox, paths
from .contracts import GAME_TEMPLATE, append_jsonl, errors, leaks, now_iso, read_jsonl, render, write_json

ACTIONS = ("approve", "edit", "delete", "reject")
EDITABLE = ("type", "prompt", "choices", "answer", "time_limit_s")


def load(lesson_id: str) -> dict:
    quiz = outbox.load(lesson_id, "quiz")
    if quiz is None:
        raise HTTPException(404, "Quiz not found or outbox not ready")
    return quiz


def save(lesson_id: str, quiz: dict) -> None:
    problems = errors("quiz", quiz)
    if problems:
        raise HTTPException(422, problems)
    write_json(paths.outbox_dir(lesson_id) / "quiz.json", quiz)


def next_edit_id() -> str:
    numbers = [int(m.group(1)) for e in read_jsonl(paths.EDITS) if (m := re.fullmatch(r"E(\d+)", str(e.get("edit_id", ""))))]
    return f"E{max(numbers, default=0) + 1}"


def review(lesson_id: str, action: str, q_id: str, changes: dict | None = None) -> dict:
    """Apply a review action to one question and return the edit_event that was written."""
    if action not in ACTIONS:
        raise HTTPException(422, f"action must be one of {ACTIONS}")
    quiz = load(lesson_id)
    if quiz["status"] != "pending":
        raise HTTPException(409, f"Quiz is already {quiz['status']}")
    index = next((i for i, q in enumerate(quiz["questions"]) if q["q_id"] == q_id), None)
    if index is None:
        raise HTTPException(404, f"Question {q_id} not found")
    before = quiz["questions"][index]
    after = before

    if action == "edit":
        unknown = set(changes or {}) - set(EDITABLE)
        if not changes or unknown:
            raise HTTPException(422, f"edit needs changes limited to {EDITABLE}")
        # q_id, kp_id and source cannot be changed: the source must be the teacher's actual words from class
        after = {**before, **changes}
        if after["type"] != "mcq":
            after.pop("choices", None)
        quiz["questions"][index] = after
    elif action in ("delete", "reject"):
        if len(quiz["questions"]) == 1:
            raise HTTPException(409, "Cannot remove the last question; reject the whole quiz instead")
        del quiz["questions"][index]
        after = {}

    if action != "approve":
        save(lesson_id, quiz)
    event = {"edit_id": next_edit_id(), "quiz_id": quiz["quiz_id"], "q_id": q_id, "action": action,
             "before": before, "after": after, "at": now_iso()}
    problems = errors("edit_event", event)
    if problems:
        raise HTTPException(500, problems)
    append_jsonl(paths.EDITS, event)
    return event


def publish(lesson_id: str) -> dict:
    """Publish (A2 approved): regenerate game.html, status -> published."""
    quiz = load(lesson_id)
    if quiz["status"] not in ("pending", "approved"):
        raise HTTPException(409, f"Quiz is already {quiz['status']}")
    html = render(GAME_TEMPLATE.read_text(encoding="utf-8"), quiz)
    problems = leaks(html, quiz)
    if problems:
        raise HTTPException(500, problems)
    (paths.outbox_dir(lesson_id) / "game.html").write_text(html, encoding="utf-8")
    quiz["status"] = "published"
    save(lesson_id, quiz)
    return quiz


def reject(lesson_id: str) -> dict:
    """Reject the whole quiz (A2 not approved): the questions are not published."""
    quiz = load(lesson_id)
    if quiz["status"] == "published":
        raise HTTPException(409, "Quiz is already published")
    quiz["status"] = "rejected"
    save(lesson_id, quiz)
    return quiz


def published(quiz_id: str) -> tuple[str, dict]:
    """For /play: return only published quizzes. Unpublished and missing both look like 404, so the review status is not exposed."""
    lesson_id = quiz_id.removeprefix("Q-")
    quiz = outbox.load(lesson_id, "quiz")
    if quiz is None or quiz.get("quiz_id") != quiz_id or quiz.get("status") != "published":
        raise HTTPException(404, "Game not found")
    return lesson_id, quiz
