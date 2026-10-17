"""/screenpipe: the console's Recording panel (status, start/stop recording, latest content, generate the quiz game now).

Local-only like every console page. The transcript and screen text returned by /screenpipe/recent are shown to the
teacher and nothing else: not stored, never sent to the Hub (privacy boundary, DESIGN.md §0).
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from .. import screenpipe

router = APIRouter(prefix="/screenpipe", tags=["screenpipe"])


@router.get("/status")
def status():
    return screenpipe.status()


@router.post("/recording/start")
def start_recording():
    return screenpipe.start_recording()


@router.post("/recording/stop")
def stop_recording():
    return screenpipe.stop_recording()


@router.get("/recent")
def recent(minutes: int = Query(10, ge=1, le=120)):
    return {"minutes": minutes, "items": screenpipe.recent(minutes)}


@router.post("/process")
def process():
    """Generate the quiz game for the last lesson now (runs the pipe in the background)."""
    return screenpipe.run_pipe()


@router.get("/process")
def process_status():
    return screenpipe.last_run()
