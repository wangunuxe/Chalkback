"""老师控制台，https://localhost:4000（§6.3，负责人 C）。

所有页面（包括学生游戏 /play 和作答接口）都只允许本机访问：学生在老师电脑的浏览器里作答，不做手机端。
启动：make teacher（生成自签证书后绑定 127.0.0.1:4000）

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
