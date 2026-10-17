#!/usr/bin/env python3
"""从屏幕文字读出 Kahoot 报告页的薄弱题目并对到知识点（TA5，负责人 A）。

    python read_reports.py --days 7 --syllabus ~/.chalkback/cache/syllabus.json > weak.json

输出：alerts.weak_from_reports 的数组，例
    [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]
只用 `GET /search`，按 window_name 含 Kahoot 报告过滤（§6.1 第 4 步）。只是加分项，读不准时输出空数组（§12）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MOCK = Path(__file__).resolve().parents[2] / "contracts" / "examples" / "alerts.json"


def read_reports(days: int, syllabus: dict) -> list[dict]:
    # TODO(TA5): /search content_type=ocr, window_name≈Kahoot report, 时间窗显式指定为过去 days 天。
    raise NotImplementedError("TA5")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--syllabus", type=Path, default=Path.home() / ".chalkback" / "cache" / "syllabus.json")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    if args.mock:
        weak = json.loads(MOCK.read_text(encoding="utf-8"))["weak_from_reports"]
    else:
        weak = read_reports(args.days, json.loads(args.syllabus.read_text(encoding="utf-8")))
    json.dump(weak, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
