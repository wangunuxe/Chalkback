"""Local screenpipe API, for the console's Recording panel: status, start/stop recording, latest transcript and
screen text, and running the pipe now instead of waiting for the timetable.

Teacher's computer only. Nothing returned here is stored or sent to the Hub: it is only shown on the local console page.
Address and auth follow pipe's scripts: SCREENPIPE_URL (default http://localhost:3030) and SCREENPIPE_LOCAL_API_KEY
(screenpipe Settings > Privacy). The command that runs the pipe can be changed with CHALKBACK_PIPE_RUN.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException

PIPE_RUN = "npx -y screenpipe@latest pipe run pipe"  # installed name = folder name `pipe` (tested on Windows, see docs/SETUP.md step 4)
NOT_RUNNING = "screenpipe is closed: open the screenpipe app to record"


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


def recent(minutes: int) -> list[dict]:
    """The teacher's own speech (microphone only, not the speakers) and screen text of the last `minutes`, newest first."""
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = []
    for kind, content_type, limit in (("speech", "audio", 100), ("screen", "ocr", 30)):
        body = _call("GET", "/search", params={"content_type": content_type, "start_time": since, "limit": limit}) or {}
        for hit in body.get("data", []):
            c = hit.get("content", {})
            if kind == "speech" and str(c.get("device_type", "")).lower() != "input":
                continue
            text = (c.get("transcription") or c.get("text") or "").strip()
            if text:
                items.append({"time": c.get("timestamp"), "kind": kind, "app": c.get("app_name"), "text": text[:400]})
    return sorted(items, key=lambda i: i["time"] or "", reverse=True)


def run_pipe() -> dict:
    """Start chalkback-pipe now in the background; its results land in the outbox like a scheduled run."""
    command = shlex.split(os.environ.get("CHALKBACK_PIPE_RUN", PIPE_RUN))
    program = shutil.which(command[0])
    if program is None:
        raise HTTPException(503, f"{command[0]} not found: install Node.js, or set CHALKBACK_PIPE_RUN")
    subprocess.Popen([program, *command[1:]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"status": "started", "command": " ".join(command)}
