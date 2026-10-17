"""/review: list the outbox, missed-topic reminders, per-question review (A2), sources, approve sharing coverage data (A3) (TC3).

- Review actions live in quizzes.py: rewrite quiz.json and append an edit_event to state/edits.jsonl.
- When sharing is approved, share.to_coverage_share() builds the upload, which is validated against the coverage_share schema before sending;
  if the Hub is unreachable or refuses, return 502 and do not record it locally as shared.
- /console is the review page (HTML) for the teacher; everything else is a JSON API.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .. import outbox, paths, quizzes, share
from ..contracts import errors, now_iso, read_json, write_json
from ..hub_client import from_config, hub_error

router = APIRouter(tags=["review"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class ReviewActionRequest(BaseModel):
    action: str  # approve / edit / delete / reject
    q_id: str
    changes: dict | None = None  # only for edit: type / prompt / choices / answer / time_limit_s


def lesson_data(lesson_id: str) -> dict:
    quiz = outbox.load(lesson_id, "quiz")
    if quiz is None:
        raise HTTPException(404, "Outbox not ready")
    return {
        "quiz": quiz,
        "alerts": outbox.load(lesson_id, "alerts"),
        "coverage": outbox.load(lesson_id, "coverage"),
        "kp_stats": read_json(paths.kp_stats(quiz["quiz_id"])),
        "share": next((s for s in read_json(paths.SHARES, []) if s["lesson_id"] == lesson_id), None),
    }


@router.get("/review")
def list_lessons():
    return {"lessons": outbox.ready_lessons()}


@router.get("/review/{lesson_id}")
def lesson_detail(lesson_id: str):
    return lesson_data(lesson_id)


@router.post("/review/{lesson_id}/action")
def review_action(lesson_id: str, payload: ReviewActionRequest):
    return quizzes.review(lesson_id, payload.action, payload.q_id, payload.changes)


@router.post("/review/{lesson_id}/publish")
def publish_quiz(lesson_id: str):
    quiz = quizzes.publish(lesson_id)
    return {"status": quiz["status"], "play_url": f"/play/{quiz['quiz_id']}"}


@router.post("/review/{lesson_id}/reject")
def reject_quiz(lesson_id: str):
    return {"status": quizzes.reject(lesson_id)["status"]}


@router.post("/review/{lesson_id}/share")
def share_coverage_to_hub(lesson_id: str):
    coverage = outbox.load(lesson_id, "coverage")
    if not coverage:
        raise HTTPException(404, "Coverage data not found or outbox not ready")

    coverage_share = share.to_coverage_share(coverage)
    problems = errors("coverage_share", coverage_share)
    if problems:
        raise HTTPException(422, problems)

    client = from_config()
    try:
        share_id = client.share_coverage(coverage_share)
    except Exception as e:
        raise hub_error(e)

    # The Hub replaces an earlier upload of the same lesson, and the local record is replaced the same way
    shares = [s for s in read_json(paths.SHARES, []) if s["lesson_id"] != lesson_id]
    shares.append({"share_id": share_id, "lesson_id": lesson_id, "class_id": coverage["class_id"], "shared_at": now_iso()})
    write_json(paths.SHARES, shares)
    return {"status": "shared", "share_id": share_id}


@router.get("/console", response_class=HTMLResponse)
def console_page(request: Request, lesson: str | None = None):
    lessons = outbox.ready_lessons()
    lesson_id = lesson if lesson in lessons else (lessons[0] if lessons else None)
    syllabus = read_json(paths.SYLLABUS_CACHE) or {}
    config = read_json(paths.CONFIG) or {}
    return templates.TemplateResponse(request, "console.html", {
        "lessons": lessons,
        "lesson_id": lesson_id,
        "data": lesson_data(lesson_id) if lesson_id else None,
        "kp_titles": {kp["kp_id"]: kp["title"] for kp in syllabus.get("knowledge_points", [])},
        "teacher_id": config.get("teacher_id"),
    })
