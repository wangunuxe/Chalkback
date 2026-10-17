#!/usr/bin/env python3
"""用 contracts/examples 生成一个假的 ~/.chalkback/，供 console 在上游未完成时开发（§0“用 mock 先开工”）。

    python tools/seed_mock_home.py [--home .mock-home]
    CHALKBACK_HOME=.mock-home uvicorn ...
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "contracts" / "examples"


def ex(name: str):
    return json.loads((EX / f"{name}.json").read_text(encoding="utf-8"))


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", type=Path, default=ROOT / ".mock-home")
    home = ap.parse_args().home
    if home.exists():
        shutil.rmtree(home)

    plan = ex("lesson_plan")
    quiz = ex("quiz")
    out = home / "outbox" / quiz["lesson_id"]

    write(home / "config.json", ex("config"))
    write(home / "cache" / "syllabus.json", ex("syllabus"))
    write(home / "lesson_plans" / plan["class_id"] / f"{plan['date']}.json", plan)
    write(out / "segments.json", [ex("segment")])
    for name in ("coverage", "alerts", "quiz"):
        write(out / f"{name}.json", ex(name))
    shutil.copy(ROOT / "pipe" / "templates" / "game.html", out / "game.html")
    (out / "ready").touch()

    state = home / "state"
    write(state / "style_profile.json", ex("style_profile"))
    write(state / "weights.json", ex("weights"))
    (state / "edits.jsonl").write_text(json.dumps(ex("edit_event"), ensure_ascii=False) + "\n", encoding="utf-8")
    (state / "attempts.jsonl").write_text(json.dumps(ex("attempt"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"mock home: {home}")


if __name__ == "__main__":
    main()
