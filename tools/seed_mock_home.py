#!/usr/bin/env python3
"""Generate a fake ~/.chalkback/ from contracts/examples so the console can be developed before upstream is finished (§0 "start with mocks").

    python tools/seed_mock_home.py [--home .mock-home] [--hub-url http://hub:8000] [--if-empty]
    CHALKBACK_HOME=.mock-home uvicorn ...

Clears the contents of the --home directory (keeping the directory itself, so it can be a Docker volume mount point).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "contracts" / "examples"

# as in pipe step 7, use build_game.py to inject the example quiz into the game template
sys.path.insert(0, str(ROOT / "pipe" / "scripts"))
from build_game import TEMPLATE, render  # noqa: E402


def ex(name: str):
    return json.loads((EX / f"{name}.json").read_text(encoding="utf-8"))


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", type=Path, default=ROOT / ".mock-home")
    ap.add_argument("--hub-url", help="override hub_url in config.json, e.g. http://hub:8000 inside a container")
    ap.add_argument("--if-empty", action="store_true", help="do nothing if the directory already has a config.json")
    args = ap.parse_args()
    home = args.home
    if args.if_empty and (home / "config.json").exists():
        print(f"mock home exists, skip: {home}")
        return
    if home.exists():
        for child in home.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()

    plan = ex("lesson_plan")
    quiz = ex("quiz")
    out = home / "outbox" / quiz["lesson_id"]

    config = ex("config")
    if args.hub_url:
        config["hub_url"] = args.hub_url
    write(home / "config.json", config)
    write(home / "cache" / "syllabus.json", ex("syllabus"))
    write(home / "lesson_plans" / plan["class_id"] / f"{plan['date']}.json", plan)
    # the local pipe mock runs the Monday lesson after the example lesson (current_lesson.py --mock), so prepare a lesson plan for it too
    write(home / "lesson_plans" / plan["class_id"] / "2026-10-19.json", {**plan, "date": "2026-10-19"})
    write(out / "segments.json", [ex("segment")])
    for name in ("coverage", "alerts", "quiz"):
        write(out / f"{name}.json", ex(name))
    (out / "game.html").write_text(render(TEMPLATE.read_text(encoding="utf-8"), quiz), encoding="utf-8")
    (out / "ready").touch()

    state = home / "state"
    write(state / "style_profile.json", ex("style_profile"))
    write(state / "weights.json", ex("weights"))
    (state / "edits.jsonl").write_text(json.dumps(ex("edit_event"), ensure_ascii=False) + "\n", encoding="utf-8")
    (state / "attempts.jsonl").write_text(json.dumps(ex("attempt"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"mock home: {home}")


if __name__ == "__main__":
    main()
