"""~/.chalkback/ 的目录布局（技术文档 §6.2）。开发时用 CHALKBACK_HOME 指向 mock 目录。"""
from __future__ import annotations

import os
from pathlib import Path

HOME = Path(os.environ.get("CHALKBACK_HOME", Path.home() / ".chalkback")).expanduser()

CONFIG = HOME / "config.json"
SYLLABUS_CACHE = HOME / "cache" / "syllabus.json"
LESSON_PLANS = HOME / "lesson_plans"
OUTBOX = HOME / "outbox"
STATE = HOME / "state"

STYLE_PROFILE = STATE / "style_profile.json"
EDITS = STATE / "edits.jsonl"
WEIGHTS = STATE / "weights.json"
SHARES = STATE / "shares.json"
ATTEMPTS = STATE / "attempts.jsonl"


def lesson_plan(class_id: str, date: str) -> Path:
    return LESSON_PLANS / class_id / f"{date}.json"


def outbox_dir(lesson_id: str) -> Path:
    return OUTBOX / lesson_id
