"""/style: read-only view of the style profile and the source of each rule (TC6)."""
import json

from fastapi import APIRouter

from .. import paths

router = APIRouter(prefix="/style", tags=["style"])


@router.get("")
def style_profile():
    if not paths.STYLE_PROFILE.exists():
        return {"style_profile": None}
    return {"style_profile": json.loads(paths.STYLE_PROFILE.read_text(encoding="utf-8"))}
