#!/usr/bin/env python3
"""alerts.json 的语义检查（pipe 第 5 步，TB4，负责人 B）。防止 agent 漏判或编造“以前讲过”。

    python check_alerts.py --alerts $OUT/alerts.json --lookback $WORK/lookback.json \
        [--reports $WORK/reports.json] [--syllabus ~/.chalkback/cache/syllabus.json]

检查（错误 → 退出码 1）：
- 先通过 alerts schema；lesson_id 与 lookback 一致
- 教案计划讲、本节没讲的每个知识点，恰好出现在 missed 或 covered_before 之一
- 本节讲过的、教案没计划的知识点不能出现在 missed / covered_before
- from_outbox 有记录的点必须进 covered_before，且 last_covered_at 等于那条记录
- 其余 covered_before 的 last_covered_at 必须等于某条 search_hits 的 timestamp（不许编时间）
- weak_from_reports 只能来自 read_reports.py 的输出，且知识点在考纲里
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
        errors.append(f"lesson_id {alerts['lesson_id']} 与 lookback 的 {lookback['lesson_id']} 不一致")

    cands = {c["kp_id"]: c for c in lookback["candidates"]}
    missed = [m["kp_id"] for m in alerts["missed"]]
    before = {b["kp_id"]: b for b in alerts["covered_before"]}
    seen = Counter(missed + [b["kp_id"] for b in alerts["covered_before"]])

    for kp, n in seen.items():
        if kp not in cands:
            errors.append(f"{kp} 不是“教案计划讲、本节没讲”的知识点，不应出现在 missed / covered_before")
        elif n > 1:
            errors.append(f"{kp} 同时或重复出现在 missed / covered_before")
    for kp in cands:
        if kp not in seen:
            errors.append(f"{kp} 教案计划讲、本节没讲，必须放进 missed 或 covered_before")

    for kp, b in before.items():
        cand = cands.get(kp)
        if cand is None:
            continue
        if cand["from_outbox"]:
            if not same_time(b["last_covered_at"], cand["from_outbox"]["last_covered_at"]):
                errors.append(f"{kp}: last_covered_at 应为 outbox 记录的 {cand['from_outbox']['last_covered_at']}")
        elif not any(same_time(b["last_covered_at"], h["timestamp"]) for h in cand["search_hits"]):
            errors.append(f"{kp}: last_covered_at {b['last_covered_at']} 不对应任何回查证据")
    for kp in missed:
        if cands.get(kp, {}).get("from_outbox"):
            errors.append(f"{kp}: outbox 显示 {cands[kp]['from_outbox']['lesson_id']} 讲过，应放进 covered_before")

    if reports is not None:
        allowed = {(r["kp_id"], r["seen_at"]) for r in reports}
        for w in alerts["weak_from_reports"]:
            if not any(kp == w["kp_id"] and same_time(at, w["seen_at"]) for kp, at in allowed):
                errors.append(f"weak_from_reports {w['kp_id']} 不在 read_reports.py 的输出里")
    if syllabus is not None:
        known = {kp["kp_id"] for kp in syllabus["knowledge_points"]}
        errors += [f"weak_from_reports {w['kp_id']} 不在考纲里" for w in alerts["weak_from_reports"] if w["kp_id"] not in known]
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
