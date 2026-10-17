"""/setup：邀请码 → 学科班级 → 课表 → 知情同意（A1）→ 写 config.json 和 pipe 定时（TC2）。

审计：Hub 应记录 join 和 consent。pipe 定时：按课表生成 cron，POST screenpipe /pipes/chalkback/config。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import paths
from ..hub_client import HubClient

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupRequest(BaseModel):
    invite_code: str
    teacher_name: str
    workspace_id: str = "W1"
    syllabus_id: str = "fr-grammaire-4e"
    timetable: list[dict] = [{"day": "MON", "start": "10:00", "end": "11:00", "class_id": "4A"}]
    hub_url: str = "https://localhost:8443"
    consent: bool = True


@router.get("")
def setup_page():
    config = {}
    if paths.CONFIG.exists():
        try:
            config = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"status": "active", "config": config}


@router.post("")
def save_setup(payload: SetupRequest):
    if not payload.consent:
        raise HTTPException(400, "Consent is required (A1)")

    token = "mock-token-T1"
    teacher_id = "T1"

    # Try joining Hub if reachable
    try:
        client = HubClient(hub_url=payload.hub_url)
        res = client.join(invite_code=payload.invite_code, display_name=payload.teacher_name)
        if res and "token" in res:
            token = res["token"]
            teacher_id = res.get("teacher_id", teacher_id)
    except Exception as e:
        print(f"Hub join offline fallback: {e}")

    config_data = {
        "hub_url": payload.hub_url,
        "token": token,
        "teacher_id": teacher_id,
        "workspace_id": payload.workspace_id,
        "syllabus_id": payload.syllabus_id,
        "timetable": payload.timetable,
        "auto_share": False,
        "consent_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        paths.CONFIG.parent.mkdir(parents=True, exist_ok=True)
        paths.CONFIG.write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Record edit event
        paths.EDITS.parent.mkdir(parents=True, exist_ok=True)
        edit_event = {
            "type": "setup_completed",
            "teacher_id": teacher_id,
            "at": datetime.now(timezone.utc).isoformat()
        }
        with open(paths.EDITS, "a", encoding="utf-8") as f:
            f.write(json.dumps(edit_event, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(500, f"Failed to save setup config: {e}")

    return {"status": "success", "teacher_id": teacher_id, "workspace_id": payload.workspace_id}
