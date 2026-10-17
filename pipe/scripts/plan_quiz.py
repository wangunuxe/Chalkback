#!/usr/bin/env python3
"""Allocate the number of questions by coverage time and weights (pipe step 7, owner B).

    python plan_quiz.py --coverage <outbox>/coverage.json [--weights ~/.chalkback/state/weights.json] [--n 5]

Only knowledge points taught in this lesson (covered=true) are tested. Score = minutes × weight (points missing from weights.json count as 1.0).
- At most n points taught: each point gets 1 question guaranteed, and the rest are split by score using the largest remainder method.
- More than n points taught: the n highest-scoring points get 1 question each.
Ties are ordered by kp_id so results are reproducible.

Output: {"n": 5, "allocation": {"KP03": 3, "KP01": 2}, "scores": {...}}
When no knowledge point was taught in this lesson, outputs an empty allocation with exit code 2 (no quiz for this lesson).
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
    # when every score is 0 (taught but with zero duration), split evenly
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
            print(f"weights.json belongs to class {weights.get('class_id')}, not {coverage['class_id']}; ignoring", file=sys.stderr)
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
