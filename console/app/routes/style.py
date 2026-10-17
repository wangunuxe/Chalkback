"""/style：只读展示风格文件及每条规则的来源（TC6）。"""
import json

from fastapi import APIRouter

from .. import paths

router = APIRouter(prefix="/style", tags=["style"])


@router.get("")
def style_profile():
    if not paths.STYLE_PROFILE.exists():
        return {"style_profile": None}
    return {"style_profile": json.loads(paths.STYLE_PROFILE.read_text(encoding="utf-8"))}
