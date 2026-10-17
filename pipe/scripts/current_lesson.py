#!/usr/bin/env python3
"""确定要处理的那节课（pipe 第 1 步，负责人 B）。

    python current_lesson.py [--now 2026-10-19T11:05:00+02:00] [--days 7]

读 config.json 的课表，从 --now 往回找最近一节**已经结束**的课（最多回看 --days 天），输出：

    {"lesson_id": "L-T1-20261019-1000", "teacher_id": "T1", "class_id": "4A", "date": "2026-10-19",
     "start": "2026-10-19T10:00:00+02:00", "end": "2026-10-19T11:00:00+02:00",
     "syllabus_id": "...", "outbox": ".../outbox/L-T1-20261019-1000", "ready": false,
     "lesson_plan": ".../lesson_plans/4A/2026-10-19.json" 或 null}

ready 为 true 表示这节课已经处理过，pipe 应直接结束（B 不修改已有 ready 的目录，§6.2）。
往回找而不是只看“刚结束”，是为了让手动触发（demo 用录好的课）也能用。
找不到任何课时退出码 2。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def chalkback_home() -> Path:
    return Path(os.environ.get("CHALKBACK_HOME", Path.home() / ".chalkback")).expanduser()


def paris() -> tzinfo:
    """Europe/Paris。Windows 上 Python 没有自带时区库（需要 tzdata 包），退回本机时区。"""
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
    ap.add_argument("--now", type=datetime.fromisoformat, help="ISO 8601 带时区；默认当前时间（Europe/Paris）")
    ap.add_argument("--days", type=int, default=7, help="最多往回找几天")
    args = ap.parse_args(argv)

    home = chalkback_home()
    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    if args.now and args.now.tzinfo is None:
        ap.error("--now 必须带时区，例如 2026-10-19T11:05:00+02:00")
    # 换到 Europe/Paris 再推算，往回找时跨过夏令时切换也对
    now = (args.now or datetime.now(paris())).astimezone(paris())

    found = find_lesson(config, now, args.days)
    if found is None:
        print(f"过去 {args.days} 天课表里没有已结束的课", file=sys.stderr)
        return 2
    json.dump(describe(config, found, home), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
