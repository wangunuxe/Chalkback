#!/usr/bin/env python3
"""Semantic checks for coverage.json (pipe step 3, owner A). The schema only checks the format; this checks that the content matches the segments and the syllabus.

    python check_coverage.py --coverage <outbox>/coverage.json --segments <outbox>/segments.json \
        --syllabus ~/.chalkback/cache/syllabus.json --lesson $WORK/lesson.json

Checks (errors → exit code 1; warnings are only printed):
- coverage first passes the coverage schema; lesson_id, teacher_id, class_id match lesson.json;
  syllabus_id, syllabus_version match the syllabus
- the same knowledge point may not appear twice, and no kp_id outside the syllabus may appear
- segment_ids are all segments of this lesson (no inventing)
- minutes = sum of the segment durations; a segment recorded under n knowledge points counts 1/n for each (rule in prompts/map_kp.md), tolerance ≤ 0.2 minutes
- covered is true if and only if minutes ≥ 1.0
- warnings: a syllabus knowledge point is missing from points (map_kp.md requires listing them all); a segment is recorded under 3 or more knowledge points (2 at most)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate_file  # noqa: E402

MIN_COVERED_MINUTES = 1.0
TOLERANCE = 0.2
MAX_KPS_PER_SEGMENT = 2


def minutes(segment: dict) -> float:
    return (datetime.fromisoformat(segment["end"]) - datetime.fromisoformat(segment["start"])).total_seconds() / 60


def expected_minutes(coverage: dict, segments: list[dict]) -> dict[str, float]:
    """Compute the minutes each knowledge point should get, using the rule in map_kp.md."""
    duration = {s["segment_id"]: minutes(s) for s in segments}
    shared = Counter(sid for p in coverage["points"] for sid in p["segment_ids"])
    return {p["kp_id"]: sum(duration.get(sid, 0) / shared[sid] for sid in p["segment_ids"]) for p in coverage["points"]}


def check(coverage: dict, segments: list[dict], syllabus: dict, lesson: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for key in ("lesson_id", "teacher_id", "class_id"):
        if coverage[key] != lesson.get(key):
            errors.append(f"{key} {coverage[key]!r} does not match lesson.json's {lesson.get(key)!r}")
    if coverage["syllabus_id"] != syllabus["syllabus_id"] or coverage["syllabus_version"] != syllabus["version"]:
        errors.append(f"syllabus should be {syllabus['syllabus_id']} v{syllabus['version']}, "
                      f"not {coverage['syllabus_id']} v{coverage['syllabus_version']}")

    syllabus_kps = [kp["kp_id"] for kp in syllabus["knowledge_points"]]
    counts = Counter(p["kp_id"] for p in coverage["points"])
    errors += [f"{kp} appears {n} times" for kp, n in counts.items() if n > 1]
    errors += [f"{kp} is not in the syllabus" for kp in counts if kp not in syllabus_kps]
    warnings += [f"syllabus {kp} does not appear in points" for kp in syllabus_kps if kp not in counts]

    seg_ids = {s["segment_id"] for s in segments}
    for p in coverage["points"]:
        errors += [f"{p['kp_id']}: segment {sid} is not a segment of this lesson" for sid in p["segment_ids"] if sid not in seg_ids]

    expected = expected_minutes(coverage, segments)
    for p in coverage["points"]:
        want = expected[p["kp_id"]]
        if abs(p["minutes"] - want) > TOLERANCE:
            errors.append(f"{p['kp_id']}: minutes should be about {want:.1f} (from the segment durations), not {p['minutes']}")
        if p["covered"] != (p["minutes"] >= MIN_COVERED_MINUTES):
            errors.append(f"{p['kp_id']}: covered should be {p['minutes'] >= MIN_COVERED_MINUTES} (only minutes ≥ {MIN_COVERED_MINUTES} counts as taught)")

    shared = Counter(sid for p in coverage["points"] for sid in p["segment_ids"])
    warnings += [f"segment {sid} is recorded under {n} knowledge points (at most {MAX_KPS_PER_SEGMENT})" for sid, n in shared.items() if n > MAX_KPS_PER_SEGMENT]
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", required=True, type=Path)
    ap.add_argument("--segments", required=True, type=Path)
    ap.add_argument("--syllabus", required=True, type=Path)
    ap.add_argument("--lesson", required=True, type=Path, help="output of current_lesson.py ($WORK/lesson.json)")
    args = ap.parse_args(argv)

    schema_errors = validate_file("coverage", args.coverage)
    if schema_errors:
        print("\n".join(schema_errors), file=sys.stderr)
        return 1

    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    errors, warnings = check(load(args.coverage), load(args.segments), load(args.syllabus), load(args.lesson))
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print(f"ok  {args.coverage}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
