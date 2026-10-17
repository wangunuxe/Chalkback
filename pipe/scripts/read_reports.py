#!/usr/bin/env python3
"""Read weak questions from Kahoot report pages in the screen text and map them to knowledge points (TA5, owner A).

    python read_reports.py --days 7 --syllabus ~/.chalkback/cache/syllabus.json --out $WORK/reports.json [--mock]

Output (written to --out): the weak_from_reports list for alerts, e.g.
    [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]

Approach:
- Only screenpipe GET /search is used (reusing extract_segments.search): OCR text whose window title contains Kahoot, fetched page by page.
- Find weak questions line by line: lines with accuracy below 50% (e.g. "23%"), or the few lines after "difficult questions / questions difficiles / need help /
  à revoir". Map each weak line plus the line above it (usually the question text) to a syllabus knowledge point.
- Score knowledge points (2 for a title hit, 1 per keyword) and take only a unique top score; ties are skipped rather than tagging several knowledge points.
- Knowledge points and keywords come only from the syllabus file; no subject-specific words are built in.

Exit code: 0 = success (outputs [] when no report is found); 1 = the syllabus could not be read or screenpipe could not be reached (also writes [], and explains why on stderr).
This step is only a bonus (§12); a failure does not affect later steps, but weak points are never invented.
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
import extract_segments  # noqa: E402  A's screenpipe client (including SCREENPIPE_URL and auth)
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
    """Whole-word match ("cod" must not match "code")."""
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
    """Lines in a report page meaning "many people got this wrong", together with the line above (the question text)."""
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
    # Whether window_name matches as a substring has not been tested yet (TA1), so filter again here
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
    ap.add_argument("--days", type=int, default=7, help="days to look back, default 7")
    ap.add_argument("--syllabus", type=Path, required=True, help="syllabus file (cache/syllabus.json)")
    ap.add_argument("--out", type=Path, required=True, help="output file")
    ap.add_argument("--mock", action="store_true", help="local development: output weak_from_reports from contracts/examples/alerts.json")
    args = ap.parse_args(argv)

    code, results = 0, []
    try:
        if args.mock:
            results = json.loads(MOCK.read_text(encoding="utf-8"))["weak_from_reports"]
        else:
            results = read_reports(args.days, load_kps(args.syllabus))
    except Exception as e:  # syllabus unreadable or screenpipe unreachable: write [], never invent
        print(f"[read_reports] failed, writing []: {e}", file=sys.stderr)
        code = 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[read_reports] {len(results)} weak knowledge points -> {args.out}")
    return code


if __name__ == "__main__":
    sys.exit(main())
