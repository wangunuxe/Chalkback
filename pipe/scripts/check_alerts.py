#!/usr/bin/env python3
"""Semantic checks for alerts.json (pipe step 5, TB4, owner B). Stops the agent from missing a point or inventing "taught before".

    python check_alerts.py --alerts $OUT/alerts.json --lookback $WORK/lookback.json \
        [--reports $WORK/reports.json] [--syllabus ~/.chalkback/cache/syllabus.json]

Checks (errors → exit code 1):
- first passes the alerts schema; lesson_id matches lookback
- every knowledge point planned in the lesson plan but not taught in this lesson appears in exactly one of missed or covered_before
- knowledge points taught in this lesson, or not planned in the lesson plan, must not appear in missed / covered_before
- points with a from_outbox record must go into covered_before, with last_covered_at equal to that record
- for the remaining covered_before entries, last_covered_at must equal the timestamp of some search_hits entry (no invented times)
- weak_from_reports may only come from the output of read_reports.py, and its knowledge points must be in the syllabus
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_lesson import chalkback_home  # noqa: E402
from validate import validate_file  # noqa: E402


def same_time(a: str, b: str) -> bool:
    return datetime.fromisoformat(a) == datetime.fromisoformat(b)


def check(alerts: dict, lookback: dict, reports: list[dict] | None, syllabus: dict | None) -> list[str]:
    errors = []
    if alerts["lesson_id"] != lookback["lesson_id"]:
        errors.append(f"lesson_id {alerts['lesson_id']} does not match lookback's {lookback['lesson_id']}")

    cands = {c["kp_id"]: c for c in lookback["candidates"]}
    missed = [m["kp_id"] for m in alerts["missed"]]
    before = {b["kp_id"]: b for b in alerts["covered_before"]}
    seen = Counter(missed + [b["kp_id"] for b in alerts["covered_before"]])

    for kp, n in seen.items():
        if kp not in cands:
            errors.append(f"{kp} is not a knowledge point 'planned in the lesson plan but not taught in this lesson', so it must not appear in missed / covered_before")
        elif n > 1:
            errors.append(f"{kp} appears in both or more than once in missed / covered_before")
    for kp in cands:
        if kp not in seen:
            errors.append(f"{kp} was planned in the lesson plan but not taught in this lesson, so it must go into missed or covered_before")

    for kp, b in before.items():
        cand = cands.get(kp)
        if cand is None:
            continue
        if cand["from_outbox"]:
            if not same_time(b["last_covered_at"], cand["from_outbox"]["last_covered_at"]):
                errors.append(f"{kp}: last_covered_at should be the outbox record's {cand['from_outbox']['last_covered_at']}")
        elif not any(same_time(b["last_covered_at"], h["timestamp"]) for h in cand["search_hits"]):
            errors.append(f"{kp}: last_covered_at {b['last_covered_at']} does not match any look-back evidence")
    for kp in missed:
        if cands.get(kp, {}).get("from_outbox"):
            errors.append(f"{kp}: outbox shows it was taught in {cands[kp]['from_outbox']['lesson_id']}, so it should go into covered_before")

    if reports is not None:
        allowed = {(r["kp_id"], r["seen_at"]) for r in reports}
        for w in alerts["weak_from_reports"]:
            if not any(kp == w["kp_id"] and same_time(at, w["seen_at"]) for kp, at in allowed):
                errors.append(f"weak_from_reports {w['kp_id']} is not in the output of read_reports.py")
    if syllabus is not None:
        known = {kp["kp_id"] for kp in syllabus["knowledge_points"]}
        errors += [f"weak_from_reports {w['kp_id']} is not in the syllabus" for w in alerts["weak_from_reports"] if w["kp_id"] not in known]
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alerts", required=True, type=Path)
    ap.add_argument("--lookback", required=True, type=Path)
    ap.add_argument("--reports", type=Path)
    ap.add_argument("--syllabus", type=Path, default=chalkback_home() / "cache" / "syllabus.json")
    args = ap.parse_args(argv)

    schema_errors = validate_file("alerts", args.alerts)
    if schema_errors:
        print("\n".join(schema_errors), file=sys.stderr)
        return 1

    load = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
    errors = check(load(args.alerts), load(args.lookback), load(args.reports), load(args.syllabus))
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print(f"ok  {args.alerts}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
