"""Teacher console, https://localhost:4000 (§6.3, owner: C).

Every page (including the student game /play and the answer endpoint) is local-only: students answer in the browser on the teacher's computer; there is no mobile version.
Start: make teacher (generates a self-signed certificate, then binds 127.0.0.1:4000)

CONSOLE_TRUSTED_NETS (comma-separated networks) is only for the Docker dev environment: inside the container, the source address is the bridge address, not 127.0.0.1.
Only set it when the host port is bound to 127.0.0.1; otherwise it opens the teacher pages to the LAN.
"""
from __future__ import annotations

import ipaddress
import os

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from .routes import play, review, setup, shares, style

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
TRUSTED_NETS = [ipaddress.ip_network(n.strip()) for n in os.environ.get("CONSOLE_TRUSTED_NETS", "").split(",") if n.strip()]

app = FastAPI(title="ChalkBack console")


def is_local(host: str) -> bool:
    if host in LOCAL_HOSTS:
        return True
    try:
        return any(ipaddress.ip_address(host) in net for net in TRUSTED_NETS)
    except ValueError:
        return False


@app.middleware("http")
async def local_only(request: Request, call_next):
    client = request.client.host if request.client else ""
    if not is_local(client):
        return PlainTextResponse("Forbidden", status_code=403)
    return await call_next(request)


@app.get("/")
def index():
    return RedirectResponse("/console")


for module in (setup, review, play, shares, style):
    app.include_router(module.router)
