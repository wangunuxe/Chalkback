"""老师控制台，http://localhost:4000（§6.3，负责人 C）。

老师页面只允许本机访问；/play 及作答接口对校园网开放（学生手机）。
启动：uvicorn app.main:app --host 0.0.0.0 --port 4000
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from .routes import play, review, setup, shares, style

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
PUBLIC_PREFIXES = ("/play/",)

app = FastAPI(title="ChalkBack console")


@app.middleware("http")
async def local_only(request: Request, call_next):
    client = request.client.host if request.client else ""
    if client not in LOCAL_HOSTS and not request.url.path.startswith(PUBLIC_PREFIXES):
        return PlainTextResponse("Forbidden", status_code=403)
    return await call_next(request)


@app.get("/")
def index():
    return RedirectResponse("/review")


for module in (setup, review, play, shares, style):
    app.include_router(module.router)
