#!/usr/bin/env python3
"""Generate this lesson's student game page from templates/game.html (pipe step 7, owner B).

    python build_game.py --quiz <outbox>/quiz.json --out <outbox>/game.html

The console does the scoring (H9 convention): the page contains only the questions, never answer, source or kp_id.
Even with the browser's "view source", students cannot get the answers or quotes from the lesson. The output is checked again after generation; on any leak it errors out and writes no file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "game.html"
PLACEHOLDER = "/*QUIZ_JSON*/ null"
PUBLIC_FIELDS = ("q_id", "type", "prompt", "choices", "time_limit_s")


def public_quiz(quiz: dict) -> dict:
    return {
        "quiz_id": quiz["quiz_id"],
        "questions": [{k: q[k] for k in PUBLIC_FIELDS if k in q} for q in quiz["questions"]],
    }


def render(template: str, quiz: dict) -> str:
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"the template must contain exactly one {PLACEHOLDER!r}")
    # keep a </script> in question text from ending the script early
    payload = json.dumps(public_quiz(quiz), ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def leaks(html: str, quiz: dict) -> list[str]:
    found = []
    for q in quiz["questions"]:
        src = q["source"]
        if src["quote"] in html:
            found.append(f"{q['q_id']}: a quote from the lesson appears in the page")
        if src["segment_id"] in html:
            found.append(f"{q['q_id']}: segment_id appears in the page")
    for key in ('"answer"', '"source"', '"frame_ids"'):
        if key in html:
            found.append(f"the page contains the {key} field")
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--template", type=Path, default=TEMPLATE)
    args = ap.parse_args(argv)

    quiz = json.loads(args.quiz.read_text(encoding="utf-8"))
    html = render(args.template.read_text(encoding="utf-8"), quiz)
    problems = leaks(html, quiz)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    args.out.write_text(html, encoding="utf-8")
    print(f"ok  {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
