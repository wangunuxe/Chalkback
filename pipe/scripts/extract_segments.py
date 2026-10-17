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
from datetime import datetime, timedelta
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SCREENPIPE_URL = os.environ.get("SCREENPIPE_URL", "http://localhost:3030")
MOCK = Path(__file__).resolve().parents[2] / "contracts" / "examples" / "segment.json"


def search(**params) -> dict:
    """GET /search 的薄封装。参数见 §6.1：content_type、start_time、end_time、app_name、window_name、q、limit、offset。"""
    url = f"{SCREENPIPE_URL}/search?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    api_key = os.environ.get("SCREENPIPE_LOCAL_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_all_items(content_type: str, start: str, end: str) -> list[dict]:
    """分页拉取指定时间窗内的所有 screenpipe 记录。"""
    items = []
    limit = 100
    offset = 0

    while True:
        res = search(
            content_type=content_type,
            start_time=start,
            end_time=end,
            limit=limit,
            offset=offset,
        )
        batch = res.get("data", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    return items


def extract(lesson_id: str, start: str, end: str) -> list[dict]:
    """分页取 audio(device_type=input) 和 ocr，按换页切分并对齐，生成 segment 列表。"""
    # 1. 抓取麦克风转写，过滤仅麦克风输入
    raw_audio = fetch_all_items("audio", start, end)
    audio_records = []
    for item in raw_audio:
        content = item.get("content", {})
        if item.get("type") == "Audio" and content.get("device_type") == "input":
            ts = content.get("timestamp")
            if ts:
                audio_records.append(
                    {
                        "id": content.get("audio_transcription_id"),
                        "text": content.get("transcription", "").strip(),
                        "time": datetime.fromisoformat(ts),
                    }
                )
    audio_records.sort(key=lambda x: x["time"])

    # 2. 抓取 OCR 课件文字
    raw_ocr = fetch_all_items("ocr", start, end)
    ocr_records = []
    for item in raw_ocr:
        content = item.get("content", {})
        if item.get("type") == "OCR":
            text = content.get("text", "").strip()
            ts = content.get("timestamp")
            if text and ts:
                ocr_records.append(
                    {
                        "frame_id": content.get("frame_id"),
                        "text": text,
                        "app_name": content.get("app_name", "Presentation"),
                        "time": datetime.fromisoformat(ts),
                    }
                )
    ocr_records.sort(key=lambda x: x["time"])

    # 3. 按换页（OCR 文本变化）提取关键节点；过滤短时间内的抖动
    dt_lesson_start = datetime.fromisoformat(start)
    dt_lesson_end = datetime.fromisoformat(end)

    slide_checkpoints: list[dict] = []
    last_text = ""
    for ocr in ocr_records:
        curr_text = ocr["text"]
        # 当文字发生较大变动，且距离上一个分段至少间隔 60 秒以上视为新幻灯片
        if curr_text != last_text:
            if (
                not slide_checkpoints
                or (ocr["time"] - slide_checkpoints[-1]["time"]).total_seconds() >= 60
            ):
                slide_checkpoints.append(ocr)
                last_text = curr_text

    # 兜底：若全程无 PPT 换页或纯口授，按每 3 分钟划定一个分段锚点
    if not slide_checkpoints:
        curr = dt_lesson_start
        step = timedelta(minutes=3)
        while curr < dt_lesson_end:
            slide_checkpoints.append(
                {
                    "frame_id": None,
                    "text": "",
                    "app_name": "Classroom",
                    "time": curr,
                }
            )
            curr += step

    # 4. 构建时间窗口并对齐麦克风发言与 Evidence
    segments: list[dict] = []
    for idx, cp in enumerate(slide_checkpoints, start=1):
        seg_start_dt = cp["time"]
        if idx < len(slide_checkpoints):
            seg_end_dt = slide_checkpoints[idx]["time"]
        else:
            seg_end_dt = dt_lesson_end

        # 确保时间边界合理
        if seg_end_dt <= seg_start_dt:
            continue

        # 匹配落入该区间的麦克风转写
        matched_audios = [
            a
            for a in audio_records
            if seg_start_dt <= a["time"] < seg_end_dt
        ]

        speech_parts = [a["text"] for a in matched_audios if a["text"]]
        speech = " ".join(speech_parts).strip()
        trans_ids = [
            a["id"] for a in matched_audios if a["id"] is not None
        ]

        frame_ids = [cp["frame_id"]] if cp["frame_id"] is not None else []

        segment = {
            "segment_id": f"S-{lesson_id}-{idx:03d}",
            "lesson_id": lesson_id,
            "start": seg_start_dt.isoformat(),
            "end": seg_end_dt.isoformat(),
            "speech": speech,
            "slide_text": cp["text"],
            "app_name": cp["app_name"],
            "evidence": {
                "transcription_ids": trans_ids,
                "frame_ids": frame_ids,
            },
        }
        segments.append(segment)

    return segments


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
        args.out.write_text(
            json.dumps([json.loads(MOCK.read_text(encoding="utf-8"))], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return
    segments = extract(args.lesson_id, args.start, args.end)
    args.out.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()