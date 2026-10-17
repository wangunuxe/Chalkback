"""审核题目（A2，TC3）：逐题通过 / 修改 / 删除 / 拒绝，发布或整份拒绝。

- 每个动作改写 outbox 里的 quiz.json（改完整份过 quiz schema），并追加一条 edit_event 到 state/edits.jsonl，
  pipe 第 6 步据此学习老师的风格（`pipe/scripts/style_inputs.py`）。
- 只有 status = published 的测验才会在 /play 提供；发布时用 pipe 的 build_game 重新生成 game.html，
  保证学生看到的是审核后的题目，页面里也不含答案和课上原话。
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
    """对一道题执行审核动作，返回写入的 edit_event。"""
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
        # q_id、kp_id、source 不能改：出处必须是课上真实的原话
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
    """发布（A2 通过）：重新生成 game.html，status → published。"""
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
    """整份拒绝（A2 不通过）：题目不发布。"""
    quiz = load(lesson_id)
    if quiz["status"] == "published":
        raise HTTPException(409, "Quiz is already published")
    quiz["status"] = "rejected"
    save(lesson_id, quiz)
    return quiz


def published(quiz_id: str) -> tuple[str, dict]:
    """/play 用：只返回已发布的测验。未发布、不存在都当作 404，不暴露审核状态。"""
    lesson_id = quiz_id.removeprefix("Q-")
    quiz = outbox.load(lesson_id, "quiz")
    if quiz is None or quiz.get("quiz_id") != quiz_id or quiz.get("status") != "published":
        raise HTTPException(404, "Game not found")
    return lesson_id, quiz
