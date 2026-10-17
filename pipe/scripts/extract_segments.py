#!/usr/bin/env python3
"""Fetch microphone transcripts and slide text for a time window and align them by timestamp into teaching segments (TA2, owner A).

    python extract_segments.py --lesson-id L-T1-20261017-1000 \
        --start 2026-10-17T10:00:00+02:00 --end 2026-10-17T11:00:00+02:00 \
        --out ~/.chalkback/outbox/L-T1-20261017-1000/segments.json [--mock]

Output: an array of segment objects that must pass `validate.py segment`.
Constraints (§6.1): only screenpipe `GET /search` is used; audio is taken only from device_type=input (the microphone);
requests carry Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY.

Splitting rules:
- A clear change in screen text (ocr + accessibility; similarity < 70%) counts as a slide change; each slide becomes a segment.
- Slides shorter than 2 minutes are merged into the adjacent segment (slides flipped too fast, a quick switch to another window); brief screens from a different app merge only their time, not their text.
- Segments longer than 5 minutes are split evenly. With no screen text at all, the whole lesson is cut into 5-minute pieces.
- Segments with no speech are not output (they are not teaching). If no speech was recorded for the whole lesson the output is [], which pipe step 2 treats as a failure.
- Text from mail, chat, password-manager and similar windows is always discarded (SCREEN_DENY_*) and never goes into slide_text.
- All times use the Europe/Paris offset.

The fields screenpipe returns follow demo/screenpipe_test_record.md; the accessibility field names and
the casing of device_type have not been tested yet (TA1), so both are parsed leniently here.
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

# Screen text from these apps / windows may be private and must not be treated as slide text (it stays on the teacher's computer, but should not end up as a question source either)
SCREEN_DENY_APPS = ("mail", "outlook", "messages", "slack", "whatsapp", "telegram", "signal", "discord", "1password", "bitwarden")
SCREEN_DENY_WINDOWS = ("gmail", "inbox", "boîte de réception", "messenger", "incognito", "privée", "private browsing")


def paris() -> tzinfo:
    """Europe/Paris. On Windows, Python has no bundled time zone database (it needs the tzdata package), so fall back to the local time zone."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Paris")
    except Exception:
        return datetime.now().astimezone().tzinfo


def parse_iso(ts: str) -> datetime:
    """Parse ISO 8601 with Z or a UTC offset and convert it to Europe/Paris."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(paris())


def search(**params) -> dict:
    """Thin wrapper around GET /search. Parameters: content_type, start_time, end_time, q, window_name, limit, offset, etc."""
    url = f"{SCREENPIPE_URL}/search?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    api_key = os.environ.get("SCREENPIPE_LOCAL_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_all(content_type: str, start: str, end: str, **params) -> list[dict]:
    """Fetch every record in the time window, page by page."""
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
    """Only the teacher's microphone (device_type = input), not sound played by the computer. Case-insensitive."""
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
    """Screen text from ocr and accessibility. Only OCR has a frame_id (so the screenshot can be looked back at)."""
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
    """Filter OCR jitter: only a content similarity below 70% counts as a slide change."""
    return difflib.SequenceMatcher(None, a.strip(), b.strip()).ratio() < SLIDE_CHANGE_RATIO


def slides(screen: list[dict], start: datetime, end: datetime) -> list[dict]:
    """Cut screen text into [start, end) slides at each slide change; the first slide starts at the beginning of the lesson so opening speech is not lost."""
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
    """Merge slides shorter than MIN_SEGMENT into the previous segment (the first slide into the next one). Brief screens from a different app merge only their time, not their text."""
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
        n = max(1, -(-span // MAX_SEGMENT))  # round up
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
    except urllib.error.HTTPError as e:  # older screenpipe versions do not support accessibility
        print(f"[extract_segments] accessibility unavailable ({e.code}), using ocr only", file=sys.stderr)
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
    """The example segment, switched to this lesson's lesson_id, with its time shifted to --start using its offset from the start of the example lesson."""
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
    ap.add_argument("--mock", action="store_true", help="While upstream is unfinished: output the example segment from contracts/examples (with this lesson's id and time)")
    args = ap.parse_args(argv)

    segments = mock(args.lesson_id, args.start) if args.mock else extract(args.lesson_id, args.start, args.end)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract_segments] {len(segments)} segments -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
