#!/usr/bin/env python3
"""quiz.json 的语义检查（pipe 第 7 步，负责人 B）。schema 只管格式，这里管内容是否可信。

    python check_quiz.py --quiz <outbox>/quiz.json --segments <outbox>/segments.json \
        --coverage <outbox>/coverage.json [--plan plan.json]

检查（错误 → 退出码 1；警告只打印）：
- quiz 先通过 quiz schema；quiz_id = "Q-" + lesson_id；status = pending；q_id 不重复
- 只考本节讲过的知识点；给了 --plan（plan_quiz.py 的输出）时，每个知识点的题数与分配一致
- source.segment_id 是本节的片段；source.quote 规范化后是该片段 speech 的子串（不许编造原话）
- source.frame_ids 都来自该片段的 evidence（不许编造截图 id）
- mcq：答案下标在范围内，选项规范化后不重复；fill_blank：题干有 ___，答案规范化后非空
- 警告：片段不在 coverage 给这个知识点记的 segment_ids 里；原话少于 5 个词

normalize_answer() 是填空题判分规则的草案，控制台判分必须用同一套规则（待写进 contracts/）。
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
APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'", "«": '"', "»": '"', "“": '"', "”": '"'})


def normalize_answer(s: str) -> str:
    """填空题判分：Unicode NFC、统一撇号、忽略大小写和多余空白。保留重音（vues ≠ vûes），待全员确认。"""
    s = unicodedata.normalize("NFC", s).translate(APOSTROPHES).casefold()
    return re.sub(r"\s+", " ", s).strip()


def normalize_quote(s: str) -> str:
    """原话比对：在 normalize_answer 基础上去掉标点（转写的标点不可靠），保留撇号（j'ai）。"""
    s = normalize_answer(s)
    s = "".join(" " if unicodedata.category(c).startswith("P") and c != "'" else c for c in s)
    return re.sub(r"\s+", " ", s).strip()


def check(quiz: dict, segments: list[dict], coverage: dict, plan: dict | None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    seg_by_id = {s["segment_id"]: s for s in segments}
    points = {p["kp_id"]: p for p in coverage["points"]}

    if quiz["lesson_id"] != coverage["lesson_id"]:
        errors.append(f"lesson_id {quiz['lesson_id']} 与 coverage 的 {coverage['lesson_id']} 不一致")
    if quiz["quiz_id"] != f"Q-{quiz['lesson_id']}":
        errors.append(f"quiz_id 应为 Q-{quiz['lesson_id']}")
    if quiz["status"] != "pending":
        errors.append("新生成的 quiz status 必须是 pending（发布要经老师审核 A2）")

    q_ids = Counter(q["q_id"] for q in quiz["questions"])
    errors += [f"q_id {q} 重复" for q, n in q_ids.items() if n > 1]

    for q in quiz["questions"]:
        where = q["q_id"]
        kp = q["kp_id"]
        if not points.get(kp, {}).get("covered"):
            errors.append(f"{where}: {kp} 本节没有讲过，不能出题")

        src = q["source"]
        seg = seg_by_id.get(src["segment_id"])
        if seg is None:
            errors.append(f"{where}: source.segment_id {src['segment_id']} 不是本节的片段")
        else:
            if normalize_quote(src["quote"]) not in normalize_quote(seg["speech"]):
                errors.append(f"{where}: source.quote 在片段 {seg['segment_id']} 的转写里找不到：{src['quote']!r}")
            extra = set(src["frame_ids"]) - set(seg["evidence"]["frame_ids"])
            if extra:
                errors.append(f"{where}: source.frame_ids {sorted(extra)} 不属于片段 {seg['segment_id']}")
            if kp in points and src["segment_id"] not in points[kp]["segment_ids"]:
                warnings.append(f"{where}: 片段 {src['segment_id']} 没有被 coverage 记在 {kp} 下")
        words = len(normalize_quote(src["quote"]).split())
        if words < MIN_QUOTE_WORDS:
            warnings.append(f"{where}: 原话只有 {words} 个词，可能不足以支撑这道题（要求 {MIN_QUOTE_WORDS}–25 个词）")

        if q["type"] == "mcq":
            choices = q.get("choices", [])
            if not 0 <= q["answer"] < len(choices):
                errors.append(f"{where}: answer 下标 {q['answer']} 超出选项范围")
            if len({normalize_answer(c) for c in choices}) != len(choices):
                errors.append(f"{where}: 选项有重复")
        elif q["type"] == "fill_blank":
            if "___" not in q["prompt"]:
                errors.append(f"{where}: 填空题题干要用 ___ 标出空格")
            if not normalize_answer(q["answer"]):
                errors.append(f"{where}: 填空题答案为空")

    if plan is not None:
        got = Counter(q["kp_id"] for q in quiz["questions"])
        want = plan["allocation"]
        if dict(got) != want:
            errors.append(f"各知识点题数 {dict(got)} 与 plan_quiz 分配 {want} 不一致")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, type=Path)
    ap.add_argument("--segments", required=True, type=Path)
    ap.add_argument("--coverage", required=True, type=Path)
    ap.add_argument("--plan", type=Path, help="plan_quiz.py 的输出")
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
