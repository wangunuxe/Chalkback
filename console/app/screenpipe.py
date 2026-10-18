"""Local screenpipe API, for the console's Recording panel: status, start/stop recording, and generating the quiz game
for the last lesson (running the pipe) as soon as recording stops, instead of waiting for the timetable.

Teacher's computer only. Nothing returned here is stored or sent to the Hub: it is only shown on the local console page.
Address and auth follow pipe's scripts: SCREENPIPE_URL (default http://localhost:3030) and SCREENPIPE_LOCAL_API_KEY
(screenpipe Settings > Privacy). The command that runs the pipe can be changed with CHALKBACK_PIPE_RUN.
The pipe's output goes to state/pipe-run.log so a failed run is shown to the teacher instead of failing silently.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from . import paths

PIPE_RUN = "npx -y screenpipe@latest pipe run pipe"  # installed name = folder name `pipe` (tested on Windows, see docs/SETUP.md step 4)
NOT_RUNNING = "screenpipe is closed: open the screenpipe app to record"
LOG_LINES = 15

_run: dict = {}  # the current or last pipe run of this console process: {"proc", "started_at", "command"}


def _client() -> httpx.Client:
    key = os.environ.get("SCREENPIPE_LOCAL_API_KEY", "")
    return httpx.Client(
        base_url=os.environ.get("SCREENPIPE_URL", "http://localhost:3030"),
        headers={"Authorization": f"Bearer {key}"} if key else {},
        timeout=10,
    )


def _call(method: str, path: str, *, any_status: bool = False, **kwargs):
    """One screenpipe request; errors become messages the teacher can act on."""
    try:
        with _client() as client:
            r = client.request(method, path, **kwargs)
    except httpx.HTTPError:
        raise HTTPException(502, "screenpipe is unreachable: is the screenpipe app running on this computer?")
    try:
        body = r.json()
    except ValueError:
        body = None
    # screenpipe quit but still serves saved history: recording control and device lists are unavailable
    if isinstance(body, dict) and body.get("error") == "search_only":
        raise HTTPException(409, NOT_RUNNING)
    if r.status_code in (401, 403):
        raise HTTPException(502, "screenpipe refused the API key: set SCREENPIPE_LOCAL_API_KEY (screenpipe Settings > Privacy)")
    if r.status_code >= 400 and not any_status:
        raise HTTPException(502, f"screenpipe error {r.status_code}")
    return body


def _monitor_id(item: dict):
    return item.get("monitor_id", item.get("id"))


def status() -> dict:
    health = _call("GET", "/health", any_status=True) or {}  # "degraded" comes with 503 but is still an answer
    try:
        # /audio/list answers search_only when the recording engine was quit; the device status endpoints still
        # answer in that state (all devices "not running"), so they alone cannot tell "closed" from "stopped"
        _call("GET", "/audio/list")
        devices = _call("GET", "/audio/device/status")
        screens = _call("GET", "/vision/device/status")
    except HTTPException as e:
        if e.status_code != 409:
            raise
        return {"app_open": False, "recording": False, "health": health.get("status"), "microphones": [], "screens": 0}
    microphones = [{"name": d["name"].removesuffix(" (input)"), "running": d.get("is_running", False)}
                   for d in devices if d.get("name", "").endswith("(input)")]
    running_screens = sum(1 for s in screens if s.get("is_running"))
    return {
        "app_open": True,
        "recording": any(m["running"] for m in microphones) or running_screens > 0,
        "health": health.get("status"),
        "microphones": microphones,
        "screens": running_screens,
    }


def start_recording() -> dict:
    _call("POST", "/audio/start")
    for monitor in _call("GET", "/vision/list") or []:
        _call("POST", "/vision/device/start", json={"monitor_id": _monitor_id(monitor)})
    return status()


def stop_recording() -> dict:
    _call("POST", "/audio/stop")
    for screen in _call("GET", "/vision/device/status") or []:
        if screen.get("is_running"):
            _call("POST", "/vision/device/stop", json={"monitor_id": _monitor_id(screen)})
    return status()


def log_path():
    return paths.STATE / "pipe-run.log"


def run_pipe() -> dict:
    """Start chalkback-pipe now in the background; its results land in the outbox like a scheduled run."""
    if _run and _run["proc"].poll() is None:
        raise HTTPException(409, "the quiz game is already being generated")
    command = shlex.split(os.environ.get("CHALKBACK_PIPE_RUN", PIPE_RUN))
    program = shutil.which(command[0])
    if program is None:
        raise HTTPException(503, f"{command[0]} not found: install Node.js, or set CHALKBACK_PIPE_RUN")
    log_path().parent.mkdir(parents=True, exist_ok=True)
    with open(log_path(), "wb") as log:
        proc = subprocess.Popen([program, *command[1:]], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    _run.update(proc=proc, started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), command=" ".join(command))
    return last_run()


def last_run() -> dict:
    """running / done / failed, with the end of the pipe's output when it failed."""
    if not _run:
        return {"status": "never"}
    code = _run["proc"].poll()
    result = {"status": "running" if code is None else "done" if code == 0 else "failed",
              "started_at": _run["started_at"], "command": _run["command"], "exit_code": code}
    if code not in (None, 0):
        try:
            lines = log_path().read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        result["log_tail"] = [line for line in lines if line.strip()][-LOG_LINES:]
    return result
