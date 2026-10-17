"""学校 Hub（§6.4，负责人 D）。启动：uvicorn app.main:app --port 8000"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routes import audit, coverage, dashboard, join, syllabus

app = FastAPI(title="ChalkBack Hub")

for module in (join, syllabus, coverage, dashboard, audit):
    app.include_router(module.router)

# 看板前端（TD6）
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
