"""考纲草稿、组长批准、版本（TD3，审批 A4）。未批准的版本不生效。"""
from fastapi import APIRouter, Depends

from ..auth import current_member, require
from ..mock import example

router = APIRouter(prefix="/api/syllabus", tags=["syllabus"])


@router.get("/current")
def current(_=Depends(current_member)):
    # TODO(TD3): 返回最新 status=approved 的版本
    return example("syllabus")


@router.post("")
def create_draft(syllabus: dict, _=Depends(require("head"))):
    # TODO(TD3): 按 syllabus schema 校验，存为 draft，version+1
    return {"syllabus_id": syllabus.get("syllabus_id"), "version": 2}


@router.post("/{syllabus_id}/approve")
def approve(syllabus_id: str, _=Depends(require("head"))):
    # TODO(TD3): draft → approved，写 audit_event(approve_syllabus)
    return example("syllabus")
