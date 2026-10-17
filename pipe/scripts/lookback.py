#!/usr/bin/env python3
"""Look back over the past N days to find evidence for missed-topic alerts (pipe step 5, TB4, owner B).

    python lookback.py --lesson $WORK/lesson.json --coverage $OUT/coverage.json [--days 21] [--mock]

For every knowledge point "planned in the lesson plan but not taught in this lesson", collect two kinds of evidence for the agent to judge following prompts/alerts.md:
1. from_outbox: among lessons for the same class already processed in the past N days, the most recent one whose coverage.json marks it covered. Reliable.
2. search_hits: call screenpipe /search with the syllabus keywords (audio from the microphone only, plus OCR), passing
   start_time/end_time **explicitly** (the default window is only 8 hours, §6.1). Each hit is marked with whether it falls in this class's timetable slot (in_class_slot).
   Candidates only: a keyword appearing does not mean it was taught.
With --mock, screenpipe is not called and only the outbox is checked. screenpipe errors are recorded in search_error without aborting.

Output (written only to $WORK, stays local):
    {"lesson_id", "class_id", "window": {"start", "end"}, "has_lesson_plan", "planned", "covered_now",
     "candidates": [{"kp_id", "title", "keywords", "from_outbox": {...} | null, "search_hits": [...], "search_error": null}]}
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_lesson import DAYS, chalkback_home, paris  # noqa: E402
import extract_segments  # noqa: E402  A's screenpipe client

MAX_HITS = 10
SNIPPET = 160


def lesson_start(lesson_id: str) -> datetime:
    """L-{teacher}-{YYYYMMDD}-{HHMM} → Paris time."""
    _, _, ymd, hm = lesson_id.rsplit("-", 3)
    return datetime.strptime(ymd + hm, "%Y%m%d%H%M").replace(tzinfo=paris())


def iso(dt: datetime) -> str:
    return dt.astimezone(paris()).isoformat(timespec="seconds")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def scan_outbox(outbox: Path, lesson: dict, since: datetime, until: datetime) -> dict[str, dict]:
    """Past coverage tables for the same class: kp_id → the most recent record of it being taught. The time is preferably the start of the first segment covering this point."""
    latest: dict[str, dict] = {}
    if not outbox.is_dir():
        return latest
    for d in outbox.iterdir():
        if d.name == lesson["lesson_id"]:
            continue
        coverage = load_json(d / "coverage.json")
        if not coverage or coverage.get("class_id") != lesson["class_id"]:
            continue
        try:
            started = lesson_start(coverage["lesson_id"])
        except (KeyError, ValueError):
            continue
        if not since <= started < until:
            continue
        seg_start = {s["segment_id"]: s["start"] for s in load_json(d / "segments.json") or []}
        for p in coverage.get("points", []):
            if not p.get("covered"):
                continue
            starts = [seg_start[s] for s in p.get("segment_ids", []) if s in seg_start]
            at = min(datetime.fromisoformat(s) for s in starts) if starts else started
            prev = latest.get(p["kp_id"])
            if prev is None or at > datetime.fromisoformat(prev["last_covered_at"]):
                latest[p["kp_id"]] = {"lesson_id": coverage["lesson_id"], "last_covered_at": iso(at), "minutes": p.get("minutes", 0)}
    return latest


def in_class_slot(at: datetime, timetable: list[dict], class_id: str) -> bool:
    local = at.astimezone(paris())
    hm = local.strftime("%H:%M")
    return any(s["class_id"] == class_id and s["day"] == DAYS[local.weekday()] and s["start"] <= hm < s["end"]
               for s in timetable)


def snippet(text: str, keyword: str) -> str:
    i = text.casefold().find(keyword.casefold())
    if i < 0 or len(text) <= SNIPPET:
        return text[:SNIPPET]
    start = max(0, i - SNIPPET // 2)
    return text[start:start + SNIPPET]


def search_hits(keywords: list[str], since: datetime, until: datetime, timetable: list[dict], class_id: str) -> list[dict]:
    hits: dict[tuple, dict] = {}
    for kw in keywords:
        for content_type in ("audio", "ocr"):
            res = extract_segments.search(q=kw, content_type=content_type, start_time=iso(since), end_time=iso(until), limit=20)
            for item in res.get("data", []):
                c = item.get("content", {})
                if item.get("type") == "Audio":
                    if not extract_segments.is_mic(c):
                        continue
                    key, text = ("audio", c.get("audio_transcription_id")), c.get("transcription", "")
                elif item.get("type") == "OCR":
                    key, text = ("ocr", c.get("frame_id")), c.get("text", "")
                else:
                    continue
                if key in hits or not c.get("timestamp"):
                    continue
                at = datetime.fromisoformat(c["timestamp"])
                if not since <= at < until:
                    continue
                hits[key] = {
                    "content_type": key[0],
                    "id": key[1],
                    "timestamp": iso(at),
                    "keyword": kw,
                    "text": snippet(text.strip(), kw),
                    "app_name": c.get("app_name"),
                    "window_name": c.get("window_name"),
                    "in_class_slot": in_class_slot(at, timetable, class_id),
                }
    # hits inside the class slot first, then most recent first (compared as datetimes, so correct across DST changes)
    ranked = sorted(hits.values(), key=lambda h: (not h["in_class_slot"], -datetime.fromisoformat(h["timestamp"]).timestamp()))
    return ranked[:MAX_HITS]


def lookback(lesson: dict, coverage: dict, syllabus: dict, config: dict, home: Path, days: int, mock: bool) -> dict:
    until = datetime.fromisoformat(lesson["start"])
    since = until - timedelta(days=days)
    plan = load_json(Path(lesson["lesson_plan"])) if lesson.get("lesson_plan") else None
    planned = plan["kp_ids"] if plan else []
    covered_now = [p["kp_id"] for p in coverage["points"] if p["covered"]]
    kps = {kp["kp_id"]: kp for kp in syllabus["knowledge_points"]}
    past = scan_outbox(home / "outbox", lesson, since, until)

    candidates = []
    for kp_id in planned:
        if kp_id in covered_now:
            continue
        kp = kps.get(kp_id, {"title": kp_id, "keywords": []})
        cand = {"kp_id": kp_id, "title": kp["title"], "keywords": kp["keywords"],
                "from_outbox": past.get(kp_id), "search_hits": [], "search_error": None}
        if cand["from_outbox"] is None and mock:
            # if we did not search, say so; otherwise the alert would claim "not taught in the past 21 days"
            cand["search_error"] = "mock mode: screenpipe was not queried"
        elif cand["from_outbox"] is None:
            try:
                cand["search_hits"] = search_hits(kp["keywords"] or [kp["title"]], since, until,
                                                  config.get("timetable", []), lesson["class_id"])
            except Exception as e:  # do not abort when screenpipe is unavailable; the agent records it as "could not look back"
                cand["search_error"] = f"{type(e).__name__}: {e}"
        candidates.append(cand)

    return {
        "lesson_id": lesson["lesson_id"],
        "class_id": lesson["class_id"],
        "window": {"start": iso(since), "end": iso(until)},
        "has_lesson_plan": plan is not None,
        "planned": planned,
        "covered_now": covered_now,
        "candidates": candidates,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", required=True, type=Path, help="output of current_lesson.py")
    ap.add_argument("--coverage", required=True, type=Path)
    ap.add_argument("--syllabus", type=Path)
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--mock", action="store_true", help="do not call screenpipe, only check the outbox")
    args = ap.parse_args(argv)

    home = chalkback_home()
    result = lookback(
        lesson=json.loads(args.lesson.read_text(encoding="utf-8")),
        coverage=json.loads(args.coverage.read_text(encoding="utf-8")),
        syllabus=json.loads((args.syllabus or home / "cache" / "syllabus.json").read_text(encoding="utf-8")),
        config=load_json(home / "config.json") or {},
        home=home, days=args.days, mock=args.mock,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
