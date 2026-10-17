#!/usr/bin/env python3
"""收集学习老师出题风格的材料（pipe 第 6 步，TB5，负责人 B）。

    python style_inputs.py [--days 30] [--now <ISO>] [--mock]

什么时候需要更新（§6.1 第 6 步）：风格文件不存在，或 edits.jsonl 里有比风格文件 updated_at 更新的记录。
不需要更新时只输出 {"needs_update": false, "reason": ...}，不调用 screenpipe。

需要更新时收集：
- screen_history：过去 --days 天窗口标题含出题平台（Kahoot、Quizlet、Google/Microsoft Forms）的屏幕文字，
  用 /search 的 window_name 过滤并**显式传入**起止时间；已有风格文件时只取 updated_at 之后的。
  同一窗口同样文字的帧只留最近一帧，最多 MAX_FRAMES 帧，每帧文字截到 MAX_TEXT 个字符。
- edits：比风格文件新的审核记录，附上 changed（edit 时改了哪些字段）。

输出到 $WORK/style_inputs.json（只在本机）。agent 按 prompts/learn_style.md 写新风格文件，
version 必须等于 next_version，updated_at 用 now。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_lesson import chalkback_home, paris  # noqa: E402
from lookback import iso, load_json  # noqa: E402
import extract_segments  # noqa: E402  A 的 screenpipe 客户端

PLATFORMS = {"Kahoot": "kahoot", "Quizlet": "quizlet", "Google Forms": "google_forms",
             "Formulaires Google": "google_forms", "Microsoft Forms": "microsoft_forms"}
MAX_FRAMES = 40
MAX_TEXT = 1500
PAGE = 100
MAX_PER_PLATFORM = 300


def read_edits(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def changed_fields(before: dict, after: dict) -> list[str]:
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def decide(profile: dict | None, edits: list[dict]) -> tuple[bool, str, list[dict]]:
    if profile is None:
        return True, "no_profile", edits
    since = datetime.fromisoformat(profile["updated_at"])
    new = [e for e in edits if datetime.fromisoformat(e["at"]) > since]
    if new:
        return True, "new_edits", new
    return False, "up_to_date", []


def screen_history(since: datetime, until: datetime) -> list[dict]:
    frames: dict[tuple, dict] = {}
    for term, platform in PLATFORMS.items():
        offset = 0
        while offset < MAX_PER_PLATFORM:
            res = extract_segments.search(content_type="ocr", window_name=term, start_time=iso(since),
                                          end_time=iso(until), limit=PAGE, offset=offset)
            batch = res.get("data", [])
            for item in batch:
                c = item.get("content", {})
                window = c.get("window_name") or ""
                text = (c.get("text") or "").strip()
                # 不确定 window_name 是否按子串过滤，这里再筛一次
                if (item.get("type") != "OCR" or term.casefold() not in window.casefold() or not text
                        or not c.get("timestamp") or c.get("frame_id") is None):
                    continue
                at = datetime.fromisoformat(c["timestamp"])
                if not since <= at < until:
                    continue
                key = (window, re.sub(r"\s+", " ", text))
                frame = {"frame_id": c.get("frame_id"), "timestamp": iso(at), "platform": platform,
                         "window_name": window, "text": text[:MAX_TEXT]}
                if key not in frames or at > datetime.fromisoformat(frames[key]["timestamp"]):
                    frames[key] = frame
            if len(batch) < PAGE:
                break
            offset += PAGE
    ranked = sorted(frames.values(), key=lambda f: datetime.fromisoformat(f["timestamp"]), reverse=True)
    return ranked[:MAX_FRAMES]


def collect(home: Path, now: datetime, days: int, mock: bool) -> dict:
    state = home / "state"
    profile = load_json(state / "style_profile.json")
    edits = read_edits(state / "edits.jsonl")
    needs, reason, new_edits = decide(profile, edits)
    config = load_json(home / "config.json") or {}
    result = {"needs_update": needs, "reason": reason}
    if not needs:
        return result

    since = now - timedelta(days=days)
    if profile is not None:
        since = max(since, datetime.fromisoformat(profile["updated_at"]))
    frames, error = [], None
    if not mock:
        try:
            frames = screen_history(since, now)
        except Exception as e:  # screenpipe 不可用时只用审核记录
            error = f"{type(e).__name__}: {e}"

    if not frames and not new_edits:
        return {"needs_update": False, "reason": "no_material", "search_error": error}

    return result | {
        "teacher_id": config.get("teacher_id"),
        "now": iso(now),
        "next_version": (profile["version"] + 1) if profile else 1,
        "current_profile": profile,
        "window": {"start": iso(since), "end": iso(now)},
        "screen_history": frames,
        "edits": [{"edit_id": e["edit_id"], "quiz_id": e["quiz_id"], "q_id": e["q_id"], "action": e["action"], "at": e["at"],
                   "changed": changed_fields(e["before"], e["after"]) if e["action"] == "edit" else [],
                   "before": e["before"], "after": e["after"]} for e in new_edits],
        "search_error": error,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--now", type=datetime.fromisoformat, help="ISO 8601 带时区；默认当前时间")
    ap.add_argument("--mock", action="store_true", help="不调用 screenpipe，只用审核记录")
    args = ap.parse_args(argv)
    if args.now and args.now.tzinfo is None:
        ap.error("--now 必须带时区")
    now = (args.now or datetime.now(paris())).astimezone(paris())

    json.dump(collect(chalkback_home(), now, args.days, args.mock), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
