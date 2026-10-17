"""/setup: invite code -> subject and class -> timetable -> informed consent (A1) -> write config.json and the pipe schedule (TC2).

- Consent must be explicitly checked (consent: true) to complete setup.
- Joins via Hub /api/join; if the Hub is unreachable or the invite code is invalid, returns 502 and writes no mock token.
- workspace_id, teacher_id and token all come from the join response; the current syllabus is also cached to cache/syllabus.json (needed by pipe steps 3 and 4).
- Not implemented yet: HTML wizard page, writing the pipe schedule from the timetable (POST screenpipe /pipes/chalkback/config), recording consent on the Hub (TBD).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import paths
from ..contracts import errors, now_iso, read_json, write_json
from ..hub_client import HubClient, hub_error

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupRequest(BaseModel):
    invite_code: str
    teacher_name: str
    timetable: list[dict]  # [{day: MON…SUN, start: "HH:MM", end: "HH:MM", class_id}]
    hub_url: str
    consent: bool = False


@router.get("")
def setup_page():
    return {"configured": paths.CONFIG.exists(), "config": read_json(paths.CONFIG)}


@router.post("")
def save_setup(payload: SetupRequest):
    if not payload.consent:
        raise HTTPException(400, "Consent is required (A1)")

    client = HubClient(hub_url=payload.hub_url)
    try:
        joined = client.join(invite_code=payload.invite_code, display_name=payload.teacher_name)
        syllabus = HubClient(payload.hub_url, joined["token"]).current_syllabus()
    except Exception as e:
        raise hub_error(e)

    previous = read_json(paths.CONFIG) or {}
    config = {
        "hub_url": payload.hub_url,
        "token": joined["token"],
        "teacher_id": joined["teacher_id"],
        "workspace_id": joined["workspace_id"],
        "syllabus_id": syllabus["syllabus_id"],
        "timetable": payload.timetable,
        "auto_share": previous.get("auto_share", False),
        "consent_at": now_iso(),
    }
    problems = errors("config", config)
    if problems:
        raise HTTPException(422, problems)

    write_json(paths.CONFIG, config)
    write_json(paths.SYLLABUS_CACHE, syllabus)
    return {"status": "configured", "teacher_id": config["teacher_id"], "workspace_id": config["workspace_id"]}
