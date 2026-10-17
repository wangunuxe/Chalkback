"""Read the outbox (B writes, C reads). Rule: only process directories that have a ready file (§6.2)."""
from __future__ import annotations

import json
from pathlib import Path

from . import paths


def ready_lessons() -> list[str]:
    if not paths.OUTBOX.is_dir():
        return []
    return sorted((d.name for d in paths.OUTBOX.iterdir() if (d / "ready").exists()), reverse=True)


def load(lesson_id: str, name: str) -> dict | list | None:
    """name in segments / coverage / alerts / quiz. Returns None if the directory is not ready or the file does not exist."""
    d = paths.outbox_dir(lesson_id)
    f = d / f"{name}.json"
    if not (d / "ready").exists() or not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def game_html(lesson_id: str) -> Path | None:
    f = paths.outbox_dir(lesson_id) / "game.html"
    return f if (paths.outbox_dir(lesson_id) / "ready").exists() and f.exists() else None
