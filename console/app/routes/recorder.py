"""/screenpipe: the console's Recording panel (status, start/stop recording; stopping generates the quiz game).

Local-only like every console page. Nothing here is stored or sent to the Hub (privacy boundary, DESIGN.md §0).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
    """Stop recording, then generate the quiz game for the lesson in the background: nothing else to click."""
    result = screenpipe.stop_recording()
    try:
        result["run"] = screenpipe.run_pipe()
    except HTTPException as e:
        # Already running: follow that run. Pipe cannot start (e.g. no Node.js): recording still stopped, show why
        result["run"] = screenpipe.last_run() if e.status_code == 409 else {"status": "failed", "error": e.detail}
    return result


@router.post("/process")
def process():
    """Run the pipe again for the last lesson (e.g. after a failed run)."""
    return screenpipe.run_pipe()


@router.get("/process")
def process_status():
    return screenpipe.last_run()
