#!/usr/bin/env python3
"""按时间窗取麦克风转写和课件文字，按时间戳对齐成讲解片段（TA2，负责人 A）。

    python extract_segments.py --lesson-id L-T1-20261017-1000 \
        --start 2026-10-17T10:00:00+02:00 --end 2026-10-17T11:00:00+02:00 \
        --out ~/.chalkback/outbox/L-T1-20261017-1000/segments.json [--mock]

输出：segment 对象数组，须通过 `validate.py segment`。
约束（§6.1）：只用 screenpipe `GET /search`；音频只取 device_type=input（麦克风）；
请求带 Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY。

切分规则：
- 屏幕文字（ocr + accessibility）明显变化（相似度 < 70%）算换页；每页成为一段。
- 短于 2 分钟的页并入相邻的段（换页太快、切到别的窗口一下）；不同 app 的短暂画面只并时间，不并文字。
- 长于 5 分钟的段平均切开。没有任何屏幕文字时，整节课按 5 分钟切。
- 没有讲话的段不输出（不是讲解）。整节课都没录到讲话时输出 []，pipe 第 2 步按失败处理。
- 邮件、聊天、密码管理器等窗口的文字一律丢弃（SCREEN_DENY_*），不进 slide_text。
- 时间统一为 Europe/Paris 偏移。

screenpipe 返回字段以 demo/screenpipe_test_record.md 为准；accessibility 的字段名、
device_type 的大小写还没有实测（TA1），这里都按宽松方式解析。
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, tzinfo
from pathlib import Path

SCREENPIPE_URL = os.environ.get("SCREENPIPE_URL", "http://localhost:3030")
MOCK = Path(__file__).resolve().parents[2] / "contracts" / "examples" / "segment.json"

PAGE_LIMIT = 100
SLIDE_CHANGE_RATIO = 0.70
MIN_SEGMENT = timedelta(minutes=2)
MAX_SEGMENT = timedelta(minutes=5)
MAX_FRAME_IDS = 5

# 这些 app / 窗口的屏幕文字可能是私人内容，不能当作课件文字（只在老师电脑上，但也不该进题目出处）
SCREEN_DENY_APPS = ("mail", "outlook", "messages", "slack", "whatsapp", "telegram", "signal", "discord", "1password", "bitwarden")
SCREEN_DENY_WINDOWS = ("gmail", "inbox", "boîte de réception", "messenger", "incognito", "privée", "private browsing")


def paris() -> tzinfo:
    """Europe/Paris。Windows 上 Python 没有自带时区库（需要 tzdata 包），退回本机时区。"""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Paris")
    except Exception:
        return datetime.now().astimezone().tzinfo


def parse_iso(ts: str) -> datetime:
    """解析带 Z 或时区偏移的 ISO 8601，统一转成 Europe/Paris。"""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(paris())


def search(**params) -> dict:
    """GET /search 的薄封装。参数：content_type、start_time、end_time、q、window_name、limit、offset 等。"""
    url = f"{SCREENPIPE_URL}/search?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    api_key = os.environ.get("SCREENPIPE_LOCAL_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_all(content_type: str, start: str, end: str, **params) -> list[dict]:
    """分页拉取时间窗内的全部记录。"""
    items: list[dict] = []
    offset = 0
    while True:
        batch = search(content_type=content_type, start_time=start, end_time=end,
                       limit=PAGE_LIMIT, offset=offset, **params).get("data", [])
        items.extend(batch)
        if len(batch) < PAGE_LIMIT:
            return items
        offset += PAGE_LIMIT


def is_mic(content: dict) -> bool:
    """只要老师的麦克风（device_type = input），不要电脑播放的声音。大小写不敏感。"""
    device_type = str(content.get("device_type") or "").casefold()
    if device_type:
        return device_type == "input"
    return str(content.get("device_name") or content.get("device") or "").casefold().endswith("(input)")


def audio_records(items: list[dict]) -> list[dict]:
    records = []
    for item in items:
        c = item.get("content", {})
        text = (c.get("transcription") or "").strip()
        if item.get("type") != "Audio" or not is_mic(c) or not text or not c.get("timestamp"):
            continue
        tid = c.get("audio_transcription_id", c.get("id"))
        records.append({"id": tid, "text": text, "time": parse_iso(c["timestamp"])})
    return sorted(records, key=lambda r: r["time"])


def denied(app: str, window: str) -> bool:
    app, window = app.casefold(), window.casefold()
    return any(d in app for d in SCREEN_DENY_APPS) or any(d in window for d in SCREEN_DENY_WINDOWS)


def screen_records(items: list[dict]) -> list[dict]:
    """ocr 和 accessibility 的屏幕文字。只有 OCR 有 frame_id（能回看截图）。"""
    records = []
    for item in items:
        c = item.get("content", {})
        text = (c.get("text") or "").strip()
        app, window = c.get("app_name") or "", c.get("window_name") or ""
        if item.get("type") not in ("OCR", "UI", "Accessibility") or not text or not c.get("timestamp"):
            continue
        if denied(app, window):
            continue
        frame_id = c.get("frame_id") if item.get("type") == "OCR" else None
        records.append({"frame_id": frame_id, "text": text, "app": app, "time": parse_iso(c["timestamp"])})
    return sorted(records, key=lambda r: r["time"])


def slide_changed(a: str, b: str) -> bool:
    """过滤 OCR 抖动：内容相似度低于 70% 才算换页。"""
    return difflib.SequenceMatcher(None, a.strip(), b.strip()).ratio() < SLIDE_CHANGE_RATIO


def slides(screen: list[dict], start: datetime, end: datetime) -> list[dict]:
    """把屏幕文字按换页切成 [start, end) 的页；第一页从上课开始算，保证开头的讲话不漏。"""
    pages: list[dict] = []
    for r in screen:
        if pages and not slide_changed(pages[-1]["text"], r["text"]):
            pages[-1]["frames"].append(r)
            continue
        pages.append({"start": start if not pages else r["time"], "text": r["text"], "frames": [r]})
    for page, nxt in zip(pages, pages[1:] + [None]):
        page["end"] = nxt["start"] if nxt else end
        page["app"] = Counter(f["app"] for f in page["frames"]).most_common(1)[0][0]
    return [p for p in pages if p["end"] > p["start"]]


def merge_short(pages: list[dict]) -> list[dict]:
    """短于 MIN_SEGMENT 的页并进前一段（第一页并进后一段）。不同 app 的短暂画面只并时间，不并文字。"""
    merged: list[dict] = []
    for page in pages:
        if merged and page["end"] - page["start"] < MIN_SEGMENT:
            host = merged[-1]
            host["end"] = page["end"]
            if page["app"] == host["app"]:
                host["texts"].append(page["text"])
                host["frames"].extend(page["frames"])
            continue
        merged.append({**page, "texts": [page["text"]], "frames": list(page["frames"])})
    if len(merged) > 1 and merged[0]["end"] - merged[0]["start"] < MIN_SEGMENT:
        first, second = merged[0], merged[1]
        second["start"] = first["start"]
        if first["app"] == second["app"]:
            second["texts"] = first["texts"] + second["texts"]
            second["frames"] = first["frames"] + second["frames"]
        merged = merged[1:]
    return merged


def split_long(pages: list[dict]) -> list[dict]:
    out = []
    for page in pages:
        span = page["end"] - page["start"]
        n = max(1, -(-span // MAX_SEGMENT))  # 向上取整
        step = span / n
        for i in range(n):
            out.append({**page, "start": page["start"] + step * i,
                        "end": page["end"] if i == n - 1 else page["start"] + step * (i + 1)})
    return out


def unique(values: list) -> list:
    return list(dict.fromkeys(v for v in values if v is not None))


def extract(lesson_id: str, start: str, end: str) -> list[dict]:
    lesson_start, lesson_end = parse_iso(start), parse_iso(end)
    audio = audio_records(fetch_all("audio", start, end))
    screen_items = fetch_all("ocr", start, end)
    try:
        screen_items += fetch_all("accessibility", start, end)
    except urllib.error.HTTPError as e:  # 旧版 screenpipe 不支持 accessibility
        print(f"[extract_segments] accessibility 不可用（{e.code}），只用 ocr", file=sys.stderr)
    screen = screen_records(screen_items)

    if screen:
        pages = split_long(merge_short(slides(screen, lesson_start, lesson_end)))
    else:
        pages = split_long([{"start": lesson_start, "end": lesson_end, "app": "", "texts": [""], "frames": []}])

    segments = []
    for page in pages:
        said = [a for a in audio if page["start"] <= a["time"] < page["end"]]
        if not said:
            continue
        segments.append({
            "segment_id": f"S-{lesson_id}-{len(segments) + 1:03d}",
            "lesson_id": lesson_id,
            "start": page["start"].isoformat(timespec="seconds"),
            "end": page["end"].isoformat(timespec="seconds"),
            "speech": " ".join(a["text"] for a in said),
            "slide_text": "\n".join(unique(page["texts"])),
            "app_name": page["app"],
            "evidence": {
                "transcription_ids": unique([a["id"] for a in said]),
                "frame_ids": unique([f["frame_id"] for f in page["frames"]])[:MAX_FRAME_IDS],
            },
        })
    return segments


def mock(lesson_id: str, start: str) -> list[dict]:
    """示例片段，换成这节课的 lesson_id，时间按示例里相对上课开始的偏移平移到 --start。"""
    seg = json.loads(MOCK.read_text(encoding="utf-8"))
    example_start = datetime.strptime(seg["lesson_id"][-13:], "%Y%m%d-%H%M").replace(tzinfo=parse_iso(seg["start"]).tzinfo)
    shift = parse_iso(start) - example_start
    suffix = seg["segment_id"][-3:]
    return [{**seg, "segment_id": f"S-{lesson_id}-{suffix}", "lesson_id": lesson_id,
             "start": (parse_iso(seg["start"]) + shift).isoformat(timespec="seconds"),
             "end": (parse_iso(seg["end"]) + shift).isoformat(timespec="seconds")}]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson-id", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mock", action="store_true", help="上游未完成时：输出 contracts/examples 的示例片段（换成本节课的 id 和时间）")
    args = ap.parse_args(argv)

    segments = mock(args.lesson_id, args.start) if args.mock else extract(args.lesson_id, args.start, args.end)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract_segments] {len(segments)} 个片段 -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
