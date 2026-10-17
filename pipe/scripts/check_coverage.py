#!/usr/bin/env python3
"""coverage.json 的语义检查（pipe 第 3 步，负责人 A）。schema 只管格式，这里管内容是否和片段、考纲对得上。

    python check_coverage.py --coverage <outbox>/coverage.json --segments <outbox>/segments.json \
        --syllabus ~/.chalkback/cache/syllabus.json --lesson $WORK/lesson.json

检查（错误 → 退出码 1；警告只打印）：
- coverage 先通过 coverage schema；lesson_id、teacher_id、class_id 与 lesson.json 一致；
  syllabus_id、syllabus_version 与考纲一致
- 同一个知识点不许出现两次，不许出现考纲以外的 kp_id
- segment_ids 都是本节的片段（不许编造）
- minutes = 各片段时长之和，一个片段记在 n 个知识点下时每个知识点算 1/n（规则见 prompts/map_kp.md），误差 ≤ 0.2 分钟
- covered 为 true 当且仅当 minutes ≥ 1.0
- 警告：考纲有知识点没列在 points 里（map_kp.md 要求全部列出）；一个片段记在 3 个以上知识点下（最多 2 个）
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
    """按 map_kp.md 的规则算每个知识点应得的分钟数。"""
    duration = {s["segment_id"]: minutes(s) for s in segments}
    shared = Counter(sid for p in coverage["points"] for sid in p["segment_ids"])
    return {p["kp_id"]: sum(duration.get(sid, 0) / shared[sid] for sid in p["segment_ids"]) for p in coverage["points"]}


def check(coverage: dict, segments: list[dict], syllabus: dict, lesson: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for key in ("lesson_id", "teacher_id", "class_id"):
        if coverage[key] != lesson.get(key):
            errors.append(f"{key} {coverage[key]!r} 与 lesson.json 的 {lesson.get(key)!r} 不一致")
    if coverage["syllabus_id"] != syllabus["syllabus_id"] or coverage["syllabus_version"] != syllabus["version"]:
        errors.append(f"考纲应为 {syllabus['syllabus_id']} v{syllabus['version']}，"
                      f"不是 {coverage['syllabus_id']} v{coverage['syllabus_version']}")

    syllabus_kps = [kp["kp_id"] for kp in syllabus["knowledge_points"]]
    counts = Counter(p["kp_id"] for p in coverage["points"])
    errors += [f"{kp} 出现了 {n} 次" for kp, n in counts.items() if n > 1]
    errors += [f"{kp} 不在考纲里" for kp in counts if kp not in syllabus_kps]
    warnings += [f"考纲的 {kp} 没有出现在 points 里" for kp in syllabus_kps if kp not in counts]

    seg_ids = {s["segment_id"] for s in segments}
    for p in coverage["points"]:
        errors += [f"{p['kp_id']}: 片段 {sid} 不是本节的片段" for sid in p["segment_ids"] if sid not in seg_ids]

    expected = expected_minutes(coverage, segments)
    for p in coverage["points"]:
        want = expected[p["kp_id"]]
        if abs(p["minutes"] - want) > TOLERANCE:
            errors.append(f"{p['kp_id']}: minutes 应约为 {want:.1f}（按片段时长计算），不是 {p['minutes']}")
        if p["covered"] != (p["minutes"] >= MIN_COVERED_MINUTES):
            errors.append(f"{p['kp_id']}: covered 应为 {p['minutes'] >= MIN_COVERED_MINUTES}（minutes ≥ {MIN_COVERED_MINUTES} 才算讲过）")

    shared = Counter(sid for p in coverage["points"] for sid in p["segment_ids"])
    warnings += [f"片段 {sid} 记在 {n} 个知识点下（最多 {MAX_KPS_PER_SEGMENT} 个）" for sid, n in shared.items() if n > MAX_KPS_PER_SEGMENT]
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", required=True, type=Path)
    ap.add_argument("--segments", required=True, type=Path)
    ap.add_argument("--syllabus", required=True, type=Path)
    ap.add_argument("--lesson", required=True, type=Path, help="current_lesson.py 的输出（$WORK/lesson.json）")
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
