#!/usr/bin/env python3
"""Semantic checks for quiz.json (pipe step 7, owner B). The schema only checks the format; this checks whether the content can be trusted.

    python check_quiz.py --quiz <outbox>/quiz.json --segments <outbox>/segments.json \
        --coverage <outbox>/coverage.json [--plan plan.json]

Checks (errors → exit code 1; warnings are only printed):
- the quiz first passes the quiz schema; quiz_id = "Q-" + lesson_id; status = pending; no duplicate q_id
- only knowledge points taught in this lesson are tested; with --plan (output of plan_quiz.py), the number of questions per knowledge point matches the allocation
- source.segment_id is a segment of this lesson; source.quote, normalized, is a substring of that segment's speech (no invented quotes)
- source.frame_ids all come from that segment's evidence (no invented screenshot ids)
- mcq: the answer index is in range and the normalized choices are distinct; fill_blank: the prompt contains ___ and the normalized answer is non-empty
- warnings: the segment is not among the segment_ids coverage records for this knowledge point; the quote has fewer than 5 or more than 25 words

normalize_answer() is the draft scoring rule for fill-in-the-blank questions; the console must score with the same rule (to be written into contracts/).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate_file  # noqa: E402

MIN_QUOTE_WORDS = 5
MAX_QUOTE_WORDS = 25
APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'", "«": '"', "»": '"', "“": '"', "”": '"'})


def normalize_answer(s: str) -> str:
    """Fill-in-the-blank scoring: Unicode NFC, unified apostrophes, ignore case and extra whitespace. Accents are kept (vues ≠ vûes); pending team-wide confirmation."""
    s = unicodedata.normalize("NFC", s).translate(APOSTROPHES).casefold()
    return re.sub(r"\s+", " ", s).strip()


def normalize_quote(s: str) -> str:
    """Quote matching: normalize_answer plus punctuation removal (transcript punctuation is unreliable), keeping apostrophes (j'ai)."""
    s = normalize_answer(s)
    s = "".join(" " if unicodedata.category(c).startswith("P") and c != "'" else c for c in s)
    return re.sub(r"\s+", " ", s).strip()


def check(quiz: dict, segments: list[dict], coverage: dict, plan: dict | None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    seg_by_id = {s["segment_id"]: s for s in segments}
    points = {p["kp_id"]: p for p in coverage["points"]}

    if quiz["lesson_id"] != coverage["lesson_id"]:
        errors.append(f"lesson_id {quiz['lesson_id']} does not match coverage's {coverage['lesson_id']}")
    if quiz["quiz_id"] != f"Q-{quiz['lesson_id']}":
        errors.append(f"quiz_id should be Q-{quiz['lesson_id']}")
    if quiz["status"] != "pending":
        errors.append("a newly generated quiz must have status pending (publishing requires teacher review, A2)")

    q_ids = Counter(q["q_id"] for q in quiz["questions"])
    errors += [f"q_id {q} is duplicated" for q, n in q_ids.items() if n > 1]

    for q in quiz["questions"]:
        where = q["q_id"]
        kp = q["kp_id"]
        if not points.get(kp, {}).get("covered"):
            errors.append(f"{where}: {kp} was not taught in this lesson, no questions allowed")

        src = q["source"]
        seg = seg_by_id.get(src["segment_id"])
        if seg is None:
            errors.append(f"{where}: source.segment_id {src['segment_id']} is not a segment of this lesson")
        else:
            if normalize_quote(src["quote"]) not in normalize_quote(seg["speech"]):
                errors.append(f"{where}: source.quote not found in the transcript of segment {seg['segment_id']}: {src['quote']!r}")
            extra = set(src["frame_ids"]) - set(seg["evidence"]["frame_ids"])
            if extra:
                errors.append(f"{where}: source.frame_ids {sorted(extra)} do not belong to segment {seg['segment_id']}")
            if kp in points and src["segment_id"] not in points[kp]["segment_ids"]:
                warnings.append(f"{where}: segment {src['segment_id']} is not recorded under {kp} in coverage")
        words = len(normalize_quote(src["quote"]).split())
        if words < MIN_QUOTE_WORDS:
            warnings.append(f"{where}: quote has only {words} words, possibly not enough to support this question ({MIN_QUOTE_WORDS}–{MAX_QUOTE_WORDS} words required)")
        elif words > MAX_QUOTE_WORDS:
            warnings.append(f"{where}: quote has {words} words, too long; quote only the sentence that supports this question ({MIN_QUOTE_WORDS}–{MAX_QUOTE_WORDS} words required)")

        if q["type"] == "mcq":
            choices = q.get("choices", [])
            if not 0 <= q["answer"] < len(choices):
                errors.append(f"{where}: answer index {q['answer']} is out of range of the choices")
            if len({normalize_answer(c) for c in choices}) != len(choices):
                errors.append(f"{where}: duplicate choices")
        elif q["type"] == "fill_blank":
            if "___" not in q["prompt"]:
                errors.append(f"{where}: fill-in-the-blank prompt must mark the blank with ___")
            if not normalize_answer(q["answer"]):
                errors.append(f"{where}: fill-in-the-blank answer is empty")

    if plan is not None:
        got = Counter(q["kp_id"] for q in quiz["questions"])
        want = plan["allocation"]
        if dict(got) != want:
            errors.append(f"questions per knowledge point {dict(got)} do not match the plan_quiz allocation {want}")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, type=Path)
    ap.add_argument("--segments", required=True, type=Path)
    ap.add_argument("--coverage", required=True, type=Path)
    ap.add_argument("--plan", type=Path, help="output of plan_quiz.py")
    args = ap.parse_args(argv)

    schema_errors = validate_file("quiz", args.quiz)
    if schema_errors:
        print("\n".join(schema_errors), file=sys.stderr)
        return 1

    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    errors, warnings = check(load(args.quiz), load(args.segments), load(args.coverage),
                             load(args.plan) if args.plan else None)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print(f"ok  {args.quiz}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
