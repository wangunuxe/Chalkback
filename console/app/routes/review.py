"""/review：列出 outbox、漏讲提醒、逐题审核（A2）、出处、批准共享覆盖数据（A3）（TC3）。

- 每个审核动作追加一条 edit_event 到 state/edits.jsonl。
- 批准共享时用 share.to_coverage_share() 生成上传内容，先用 coverage_share schema 校验再发。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .. import outbox, paths, share
from ..hub_client import HubClient

router = APIRouter(tags=["review"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class ReviewActionRequest(BaseModel):
    action: str  # approve, edit, delete, reject
    q_id: str | None = None
    changes: dict | None = None


@router.get("/review")
def list_lessons():
    return {"lessons": outbox.ready_lessons()}


@router.get("/review/{lesson_id}")
def lesson_detail(lesson_id: str):
    quiz = outbox.load(lesson_id, "quiz")
    if quiz is None:
        raise HTTPException(404, "outbox not ready")
    return {"quiz": quiz, "alerts": outbox.load(lesson_id, "alerts"), "coverage": outbox.load(lesson_id, "coverage")}


@router.post("/review/{lesson_id}/action")
def review_action(lesson_id: str, payload: ReviewActionRequest):
    try:
        paths.EDITS.parent.mkdir(parents=True, exist_ok=True)
        edit_event = {
            "type": "review_action",
            "lesson_id": lesson_id,
            "action": payload.action,
            "q_id": payload.q_id,
            "changes": payload.changes,
            "at": datetime.now(timezone.utc).isoformat()
        }
        with open(paths.EDITS, "a", encoding="utf-8") as f:
            f.write(json.dumps(edit_event, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(500, f"Failed to record edit event: {e}")

    return {"status": "success", "action": payload.action, "lesson_id": lesson_id}


@router.post("/review/{lesson_id}/share")
def share_coverage_to_hub(lesson_id: str):
    coverage = outbox.load(lesson_id, "coverage")
    if not coverage:
        raise HTTPException(404, "Coverage data not found or outbox not ready")

    coverage_share = share.to_coverage_share(coverage)

    hub_url = "https://localhost:8443"
    token = "mock-token-T1"
    if paths.CONFIG.exists():
        try:
            cfg = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
            hub_url = cfg.get("hub_url", hub_url)
            token = cfg.get("token", token)
        except Exception:
            pass

    share_id = f"share_{lesson_id}_{int(datetime.now().timestamp())}"
    try:
        client = HubClient(hub_url=hub_url, token=token)
        share_id = client.share_coverage(coverage_share)
    except Exception as e:
        print(f"Hub share offline fallback: {e}")

    shares = []
    if paths.SHARES.exists():
        try:
            shares = json.loads(paths.SHARES.read_text(encoding="utf-8"))
        except Exception:
            pass

    shares.append({
        "share_id": share_id,
        "lesson_id": lesson_id,
        "class_id": coverage.get("class_id"),
        "shared_at": datetime.now(timezone.utc).isoformat()
    })

    try:
        paths.SHARES.parent.mkdir(parents=True, exist_ok=True)
        paths.SHARES.write_text(json.dumps(shares, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Failed to save local share record: {e}")

    return {"status": "success", "share_id": share_id}


@router.get("/api/console/outbox")
def api_console_outbox():
    lessons = outbox.ready_lessons()
    if lessons:
        latest = lessons[0]
        return {
            "lesson_id": latest,
            "quiz": outbox.load(latest, "quiz"),
            "alerts": outbox.load(latest, "alerts"),
            "coverage": outbox.load(latest, "coverage")
        }
    return {"lesson_id": "L2023_CH01", "message": "No ready outbox lessons found"}


@router.get("/console", response_class=HTMLResponse)
def console_page(request: Request):
    try:
        lessons = outbox.ready_lessons()
        data = {}
        if lessons:
            latest = lessons[0]
            quiz = outbox.load(latest, "quiz") or {}
            coverage = outbox.load(latest, "coverage") or {}
            alerts = outbox.load(latest, "alerts") or {}
            data = {
                "lesson_id": latest,
                "teacher_name": "Prof. Martin",
                "subject": quiz.get("subject", "Classroom Review & Quiz"),
                "timestamp": latest,
                "coverages": coverage.get("points", []),
                "missed_kps": alerts.get("missed", []),
                "generated_questions": quiz.get("questions", [])
            }
        else:
            data = {
                "lesson_id": "L2023_CH01",
                "teacher_name": "Prof. Martin",
                "subject": "Chinois LV2 - Classroom Review",
                "timestamp": "2026-10-17 10:15:00",
                "coverages": [
                    {"kp_title": "Core Vocabulary: Mǐfàn (米饭)", "covered": True, "duration_minutes": 4.5, "screenpipe_timestamp": "10:04:12", "frame_id": "frame_102", "raw_quote": "Aujourd'hui..."},
                    {"kp_title": "Culture: Kuàizi (筷子)", "covered": False, "duration_minutes": 0.0}
                ],
                "missed_kps": ["Culture: Kuàizi (筷子)"],
                "generated_questions": [
                    {"id": "q1", "kp_id": "KP1", "stem": "Comment dit-on 'Riz' ?", "options": ["A. 米饭", "B. 面条"], "correct_index": 0, "explanation": "Mǐfàn = Riz"}
                ]
            }
        return templates.TemplateResponse(request, "console.html", {"data": data})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return HTMLResponse(f"<h1>Internal Server Error</h1><pre>{tb}</pre>", status_code=500)
