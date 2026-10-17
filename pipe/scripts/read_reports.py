#!/usr/bin/env python3
"""从屏幕文字读出 Kahoot 报告页的薄弱题目并对到知识点（TA5，负责人 A）。

    python read_reports.py --days 7 --syllabus ~/.chalkback/cache/syllabus.json --out $WORK/reports.json [--mock]

输出（写到 --out）：alerts 里 weak_from_reports 的列表，例如
    [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]

做法：
- 只用 screenpipe GET /search（复用 extract_segments.search）：窗口标题含 Kahoot 的 OCR 文字，分页拉取。
- 按行找薄弱题：正确率低于 50% 的行（如 “23%”），或 “difficult questions / questions difficiles / need help /
  à revoir” 之后的几行。把薄弱行和它上一行（通常是题干）对到考纲知识点。
- 对知识点打分（标题命中 2 分，每个关键词 1 分），只取唯一最高分；平分就跳过，不同时标多个知识点。
- 知识点和关键词只来自考纲文件，不内置任何学科的词。

退出码：0 = 成功（找不到报告时输出 []）；1 = 读不到考纲或连不上 screenpipe（同样写 []，并在 stderr 说明原因）。
这一步只是加分项（§12），失败不影响后面的步骤，但绝不编造薄弱点。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_segments  # noqa: E402  A 的 screenpipe 客户端（含 SCREENPIPE_URL 和认证）
from extract_segments import paris, parse_iso  # noqa: E402

MOCK = Path(__file__).resolve().parents[2] / "contracts" / "examples" / "alerts.json"
WINDOW = "kahoot"
PAGE_LIMIT = 100
MAX_PAGES = 20
WEAK_ACCURACY = 50
HEADER_LOOKAHEAD = 5
HEADERS = ("difficult question", "questions difficiles", "question difficile", "need help", "à revoir", "besoin d'aide")
PERCENT = re.compile(r"(?<![\d.,])(\d{1,3})\s?%")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s).casefold()).strip()


def contains(text: str, phrase: str) -> bool:
    """整词匹配（“cod” 不能命中 “code”）。"""
    return bool(phrase) and re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def load_kps(syllabus_path: Path) -> list[dict]:
    data = json.loads(syllabus_path.read_text(encoding="utf-8"))
    return [{"kp_id": kp["kp_id"], "title": norm(kp.get("title", "")), "keywords": [norm(k) for k in kp.get("keywords", [])]}
            for kp in data["knowledge_points"]]


def best_kp(text: str, kps: list[dict]) -> str | None:
    scores = {kp["kp_id"]: 2 * contains(text, kp["title"]) + sum(contains(text, k) for k in kp["keywords"]) for kp in kps}
    top = max(scores.values(), default=0)
    winners = [k for k, s in scores.items() if s == top]
    return winners[0] if top > 0 and len(winners) == 1 else None


def weak_lines(text: str) -> list[str]:
    """报告页里表示“这题很多人错”的行，连同上一行（题干）。"""
    lines = [norm(line) for line in text.splitlines() if line.strip()]
    flagged: set[int] = set()
    for i, line in enumerate(lines):
        if any(int(p) < WEAK_ACCURACY for p in PERCENT.findall(line)):
            flagged.add(i)
        if any(h in line for h in HEADERS):
            flagged.update(range(i + 1, min(len(lines), i + 1 + HEADER_LOOKAHEAD)))
    return [" ".join(lines[max(0, i - 1):i + 1]) for i in sorted(flagged)]


def fetch_report_frames(since: datetime, until: datetime) -> list[dict]:
    frames: list[dict] = []
    for page in range(MAX_PAGES):
        batch = extract_segments.search(content_type="ocr", window_name=WINDOW, start_time=since.isoformat(timespec="seconds"),
                                        end_time=until.isoformat(timespec="seconds"), limit=PAGE_LIMIT,
                                        offset=page * PAGE_LIMIT).get("data", [])
        frames.extend(batch)
        if len(batch) < PAGE_LIMIT:
            break
    # window_name 是否按子串匹配还没实测（TA1），这里再过滤一遍
    return [f for f in frames if f.get("type") == "OCR" and WINDOW in (f.get("content", {}).get("window_name") or "").casefold()]


def read_reports(days: int, kps: list[dict], now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(paris())
    latest: dict[str, datetime] = {}
    for frame in fetch_report_frames(now - timedelta(days=days), now):
        c = frame["content"]
        if not c.get("timestamp"):
            continue
        seen = parse_iso(c["timestamp"])
        for line in weak_lines(c.get("text") or ""):
            kp_id = best_kp(line, kps)
            if kp_id and (kp_id not in latest or seen > latest[kp_id]):
                latest[kp_id] = seen
    return [{"kp_id": k, "source": "kahoot_report", "seen_at": latest[k].isoformat(timespec="seconds")} for k in sorted(latest)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract weak knowledge points from Kahoot report pages.")
    ap.add_argument("--days", type=int, default=7, help="回看天数，默认 7")
    ap.add_argument("--syllabus", type=Path, required=True, help="考纲文件（cache/syllabus.json）")
    ap.add_argument("--out", type=Path, required=True, help="输出文件")
    ap.add_argument("--mock", action="store_true", help="本地开发：输出 contracts/examples/alerts.json 里的 weak_from_reports")
    args = ap.parse_args(argv)

    code, results = 0, []
    try:
        if args.mock:
            results = json.loads(MOCK.read_text(encoding="utf-8"))["weak_from_reports"]
        else:
            results = read_reports(args.days, load_kps(args.syllabus))
    except Exception as e:  # 读不到考纲、连不上 screenpipe：写 []，不编造
        print(f"[read_reports] 失败，输出 []：{e}", file=sys.stderr)
        code = 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[read_reports] {len(results)} 个薄弱知识点 -> {args.out}")
    return code


if __name__ == "__main__":
    sys.exit(main())
