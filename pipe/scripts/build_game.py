#!/usr/bin/env python3
"""用 templates/game.html 生成本节课的学生游戏页面（pipe 第 7 步，负责人 B）。

    python build_game.py --quiz <outbox>/quiz.json --out <outbox>/game.html

控制台判分（H9 约定）：页面里只放题目，不放 answer、source、kp_id。
学生用浏览器“查看源代码”也拿不到答案和课上原话。生成后再检查一遍，发现泄露就报错且不写文件。
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
        raise ValueError(f"模板里必须恰好有一个 {PLACEHOLDER!r}")
    # 防止题目文字里的 </script> 提前结束脚本
    payload = json.dumps(public_quiz(quiz), ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def leaks(html: str, quiz: dict) -> list[str]:
    found = []
    for q in quiz["questions"]:
        src = q["source"]
        if src["quote"] in html:
            found.append(f"{q['q_id']}: 课上原话出现在页面里")
        if src["segment_id"] in html:
            found.append(f"{q['q_id']}: segment_id 出现在页面里")
    for key in ('"answer"', '"source"', '"frame_ids"'):
        if key in html:
            found.append(f"页面里出现了 {key} 字段")
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
