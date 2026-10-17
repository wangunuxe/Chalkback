"""读取 outbox（B 写，C 读）。规则：只处理有 ready 文件的目录（§6.2）。"""
from __future__ import annotations

import json
from pathlib import Path

from . import paths


def ready_lessons() -> list[str]:
    if not paths.OUTBOX.is_dir():
        return []
    return sorted((d.name for d in paths.OUTBOX.iterdir() if (d / "ready").exists()), reverse=True)


def load(lesson_id: str, name: str) -> dict | list | None:
    """name ∈ segments / coverage / alerts / quiz。目录未 ready 或文件不存在时返回 None。"""
    d = paths.outbox_dir(lesson_id)
    f = d / f"{name}.json"
    if not (d / "ready").exists() or not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def game_html(lesson_id: str) -> Path | None:
    f = paths.outbox_dir(lesson_id) / "game.html"
    return f if (paths.outbox_dir(lesson_id) / "ready").exists() and f.exists() else None
