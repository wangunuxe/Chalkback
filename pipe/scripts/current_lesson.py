#!/usr/bin/env python3
"""Determine which lesson to process (pipe step 1, owner B).

    python current_lesson.py [--now 2026-10-19T11:05:00+02:00] [--days 7] [--mock]

Reads the timetable from config.json and searches back from --now for the most recent lesson that has **already ended** (looking back at most --days days). Output:

    {"lesson_id": "L-T1-20261019-1000", "teacher_id": "T1", "class_id": "4A", "date": "2026-10-19",
     "start": "2026-10-19T10:00:00+02:00", "end": "2026-10-19T11:00:00+02:00",
     "syllabus_id": "...", "outbox": ".../outbox/L-T1-20261019-1000", "ready": false,
     "lesson_plan": ".../lesson_plans/4A/2026-10-19.json" or null}

ready = true means this lesson has already been processed and pipe should stop right away (B never modifies a directory that already has ready, §6.2).
Searching back rather than only looking at "just ended" lets manual triggers work too (the demo uses a pre-recorded lesson).
Exit code 2 when no lesson is found.

--mock (local development, together with tools/seed_mock_home.py): pins "now" to MOCK_NOW. The example config's timetable is Monday 10:00–11:00,
and the example lesson (2026-10-17) already has a ready outbox, so mock runs the Monday lesson after it (the seed also writes a lesson plan for it).
Without pinning, the result depends on the weekday it runs on and often finds a lesson with no lesson plan.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
MOCK_NOW = "2026-10-19T11:05:00+02:00"


def chalkback_home() -> Path:
    return Path(os.environ.get("CHALKBACK_HOME", Path.home() / ".chalkback")).expanduser()


def paris() -> tzinfo:
    """Europe/Paris. On Windows, Python has no bundled time zone database (it needs the tzdata package), so fall back to the local time zone."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Paris")
    except Exception:
        return datetime.now().astimezone().tzinfo


def find_lesson(config: dict, now: datetime, days: int) -> dict | None:
    tz = now.tzinfo
    for back in range(days + 1):
        day: date = (now - timedelta(days=back)).date()
        slots = [s for s in config["timetable"] if s["day"] == DAYS[day.weekday()]]
        ended = []
        for s in slots:
            start = datetime.combine(day, time.fromisoformat(s["start"]), tz)
            end = datetime.combine(day, time.fromisoformat(s["end"]), tz)
            if end <= now:
                ended.append((end, start, s))
        if ended:
            end, start, slot = max(ended, key=lambda e: e[0])
            return {"start": start, "end": end, "class_id": slot["class_id"]}
    return None


def describe(config: dict, found: dict, home: Path) -> dict:
    start: datetime = found["start"]
    lesson_id = f"L-{config['teacher_id']}-{start:%Y%m%d}-{start:%H%M}"
    outbox = home / "outbox" / lesson_id
    plan = home / "lesson_plans" / found["class_id"] / f"{start:%Y-%m-%d}.json"
    return {
        "lesson_id": lesson_id,
        "teacher_id": config["teacher_id"],
        "class_id": found["class_id"],
        "date": start.date().isoformat(),
        "start": start.isoformat(timespec="seconds"),
        "end": found["end"].isoformat(timespec="seconds"),
        "syllabus_id": config["syllabus_id"],
        "outbox": str(outbox),
        "ready": (outbox / "ready").exists(),
        "lesson_plan": str(plan) if plan.exists() else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", type=datetime.fromisoformat, help="ISO 8601 with time zone; defaults to the current time (Europe/Paris)")
    ap.add_argument("--days", type=int, default=7, help="maximum number of days to search back")
    ap.add_argument("--mock", action="store_true", help=f"local development: pin now to {MOCK_NOW} when --now is not given")
    args = ap.parse_args(argv)

    home = chalkback_home()
    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    if args.mock and args.now is None:
        args.now = datetime.fromisoformat(MOCK_NOW)
    if args.now and args.now.tzinfo is None:
        ap.error("--now must include a time zone, e.g. 2026-10-19T11:05:00+02:00")
    # convert to Europe/Paris before computing, so searching back across a DST change is correct
    now = (args.now or datetime.now(paris())).astimezone(paris())

    found = find_lesson(config, now, args.days)
    if found is None:
        print(f"no ended lesson in the timetable in the past {args.days} days", file=sys.stderr)
        return 2
    json.dump(describe(config, found, home), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
