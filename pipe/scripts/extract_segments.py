#!/usr/bin/env python3
"""按时间窗取麦克风转写和课件文字，按时间戳对齐成讲解片段（TA2，负责人 A）。

    python extract_segments.py --lesson-id L-T1-20261017-1000 \
        --start 2026-10-17T10:00:00+02:00 --end 2026-10-17T11:00:00+02:00 \
        --out ~/.chalkback/outbox/L-T1-20261017-1000/segments.json

输出：segment 对象数组，须通过 `validate.py segment`。
约束（§6.1）：只用 screenpipe `GET /search`（只读权限下没有 /raw_sql）；音频只取 device_type=input；
按换页切分，每段约 2–5 分钟；请求带 Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY。
字段名以 TA1 实测记录（demo/screenpipe_probe/）为准。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

SCREENPIPE_URL = os.environ.get("SCREENPIPE_URL", "http://localhost:3030")
MOCK = Path(__file__).resolve().parents[2] / "contracts" / "examples" / "segment.json"


def search(**params) -> dict:
    """GET /search 的薄封装。参数见 §6.1：content_type、start_time、end_time、app_name、window_name、q、limit、offset。"""
    url = f"{SCREENPIPE_URL}/search?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ.get('SCREENPIPE_LOCAL_API_KEY', '')}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def extract(lesson_id: str, start: str, end: str) -> list[dict]:
    # TODO(TA2): 分页取 audio(device_type=input) 和 ocr/accessibility，按换页切分并对齐，
    # 生成 segment_id = f"S-{lesson_id}-{n:03d}"。
    raise NotImplementedError("TA2")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson-id", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mock", action="store_true", help="上游未完成时：输出 contracts/examples 的示例片段")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.mock:
        args.out.write_text(json.dumps([json.loads(MOCK.read_text(encoding="utf-8"))], ensure_ascii=False, indent=2), encoding="utf-8")
        return
    segments = extract(args.lesson_id, args.start, args.end)
    args.out.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
