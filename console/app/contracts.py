"""Shared helpers used by the console: contract validation, Europe/Paris time, JSON read/write, and reuse of pipe scripts.

The console and pipe run from the same repo (make teacher / Docker both include contracts/ and pipe/scripts/),
so grading rules and game page generation reuse pipe's implementation directly instead of keeping a second copy.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"

sys.path.insert(0, str(ROOT / "pipe" / "scripts"))
from build_game import TEMPLATE as GAME_TEMPLATE, leaks, render  # noqa: E402,F401
from check_quiz import normalize_answer  # noqa: E402,F401

try:
    from zoneinfo import ZoneInfo

    PARIS = ZoneInfo("Europe/Paris")
except Exception:  # fall back to the local timezone when tzdata is not installed on Windows
    PARIS = None


def now_iso() -> str:
    """ISO 8601 with timezone offset (§0 convention)."""
    now = datetime.now(PARIS) if PARIS else datetime.now().astimezone()
    return now.isoformat(timespec="seconds")


@lru_cache
def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8")))


def errors(name: str, data) -> list[str]:
    return [e.message for e in validator(name).iter_errors(data)]


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
