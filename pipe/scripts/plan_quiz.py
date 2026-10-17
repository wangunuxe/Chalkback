#!/usr/bin/env python3
"""按覆盖时长和权重分配题量（pipe 第 7 步，负责人 B）。

    python plan_quiz.py --coverage <outbox>/coverage.json [--weights ~/.chalkback/state/weights.json] [--n 5]

只考本节讲过（covered=true）的知识点。分数 = minutes × weight（weights.json 里没有的点按 1.0）。
- 讲过的点不多于 n 个：每点先保底 1 题，剩下的按分数用最大余数法分。
- 讲过的点多于 n 个：取分数最高的 n 个，每个 1 题。
分数相同时按 kp_id 排序，保证结果可复现。

输出：{"n": 5, "allocation": {"KP03": 3, "KP01": 2}, "scores": {...}}
本节没有讲过任何知识点时输出空分配并退出码 2（这节课不出题）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def allocate(scores: dict[str, float], n: int) -> dict[str, int]:
    ranked = sorted(scores, key=lambda kp: (-scores[kp], kp))
    if not ranked or n <= 0:
        return {}
    if len(ranked) >= n:
        return {kp: 1 for kp in ranked[:n]}

    alloc = {kp: 1 for kp in ranked}
    remaining = n - len(ranked)
    total = sum(scores.values())
    # 全部分数为 0（讲过但时长为 0）时平均分
    shares = {kp: (scores[kp] / total if total > 0 else 1 / len(ranked)) * remaining for kp in ranked}
    for kp in ranked:
        alloc[kp] += int(shares[kp])
    left = n - sum(alloc.values())
    for kp in sorted(ranked, key=lambda kp: (-(shares[kp] - int(shares[kp])), -scores[kp], kp))[:left]:
        alloc[kp] += 1
    return alloc


def scores_from(coverage: dict, weights: dict | None) -> dict[str, float]:
    w = {}
    if weights is not None:
        if weights.get("class_id") == coverage["class_id"]:
            w = weights["weights"]
        else:
            print(f"weights.json 属于班级 {weights.get('class_id')}，不是 {coverage['class_id']}，忽略", file=sys.stderr)
    return {p["kp_id"]: p["minutes"] * w.get(p["kp_id"], 1.0) for p in coverage["points"] if p["covered"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", required=True, type=Path)
    ap.add_argument("--weights", type=Path)
    ap.add_argument("--n", type=int, default=5)
    args = ap.parse_args(argv)

    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    weights = json.loads(args.weights.read_text(encoding="utf-8")) if args.weights and args.weights.exists() else None
    scores = scores_from(coverage, weights)
    alloc = allocate(scores, args.n)
    json.dump({"n": sum(alloc.values()), "allocation": alloc, "scores": scores}, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if alloc else 2


if __name__ == "__main__":
    sys.exit(main())
