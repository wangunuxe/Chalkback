"""老师控制台，http://localhost:4000（§6.3，负责人 C）。

老师页面只允许本机访问；/play 及作答接口对校园网开放（学生手机）。
启动：uvicorn app.main:app --host 0.0.0.0 --port 4000

CONSOLE_TRUSTED_NETS（逗号分隔的网段）只给 Docker 开发环境用：容器内看到的来源是网桥地址而不是 127.0.0.1。
只有在宿主机端口绑定到 127.0.0.1 时才能设置，否则等于把老师页面开放给局域网。
"""
from __future__ import annotations

import ipaddress
import os

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from .routes import play, review, setup, shares, style

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
TRUSTED_NETS = [ipaddress.ip_network(n.strip()) for n in os.environ.get("CONSOLE_TRUSTED_NETS", "").split(",") if n.strip()]
PUBLIC_PREFIXES = ("/play/",)

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
    if not is_local(client) and not request.url.path.startswith(PUBLIC_PREFIXES):
        return PlainTextResponse("Forbidden", status_code=403)
    return await call_next(request)


@app.get("/")
def index():
    return RedirectResponse("/review")


for module in (setup, review, play, shares, style):
    app.include_router(module.router)
