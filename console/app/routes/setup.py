"""/setup：邀请码 → 学科班级 → 课表 → 知情同意（A1）→ 写 config.json 和 pipe 定时（TC2）。

- 必须明确勾选同意（consent: true）才能完成安装。
- 通过 Hub /api/join 加入；Hub 不通或邀请码无效时返回 502，不写入任何 mock token。
- workspace_id、teacher_id、token 都取自 join 的返回；同时把当前考纲缓存到 cache/syllabus.json（pipe 第 3、4 步要用）。
- 尚未实现：HTML 向导页面、按课表写 pipe 定时（POST screenpipe /pipes/chalkback/config）、Hub 记录 consent（待定）。
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
