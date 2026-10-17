"""Grading (TC4) and learning statistics (TC5): attempts.jsonl -> kp_stats -> weights.json (§5).

Weight rules (§5 weights): default 1.0; 2.0 if the knowledge point's accuracy is below 50%; +0.5 more for weak points from the Kahoot report.
weights.json holds only one class (plan_quiz.py only uses weights with the same class_id): same class -> merge and update, different class -> overwrite.
"""
from __future__ import annotations

from collections import defaultdict

from . import outbox, paths
from .contracts import errors, normalize_answer, now_iso, read_json, read_jsonl, write_json

DEFAULT_WEIGHT = 1.0
LOW_ACCURACY = 0.5
LOW_ACCURACY_WEIGHT = 2.0
KAHOOT_BONUS = 0.5


def is_correct(question: dict, response) -> bool:
    """A timeout (response is None) always counts as wrong."""
    if response is None:
        return False
    answer, kind = question["answer"], question["type"]
    if kind == "mcq":
        # bool is a subclass of int: True must not be treated as index 1
        return isinstance(response, int) and not isinstance(response, bool) and response == answer
    if kind == "true_false":
        return isinstance(response, bool) and response == answer
    if kind == "fill_blank":
        return isinstance(response, str) and normalize_answer(response) == normalize_answer(answer)
    return False


def kp_stats(quiz: dict) -> dict:
    kp_of = {q["q_id"]: q["kp_id"] for q in quiz["questions"]}
    attempts = [a for a in read_jsonl(paths.ATTEMPTS) if a.get("quiz_id") == quiz["quiz_id"] and a.get("q_id") in kp_of]
    by_kp: dict[str, list[dict]] = defaultdict(list)
    for a in attempts:
        by_kp[kp_of[a["q_id"]]].append(a)
    return {
        "quiz_id": quiz["quiz_id"],
        "class_id": quiz["class_id"],
        "n_players": len({a["nickname"] for a in attempts}),
        "by_kp": [
            {"kp_id": kp,
             "accuracy": round(sum(a["correct"] for a in items) / len(items), 3),
             "avg_time_ms": round(sum(a["time_ms"] for a in items) / len(items))}
            for kp, items in sorted(by_kp.items())
        ],
    }


def weights(stats: dict, weak_kp_ids: set[str]) -> dict:
    current = read_json(paths.WEIGHTS)
    w = dict(current["weights"]) if current and current.get("class_id") == stats["class_id"] else {}
    # Recompute from the rules every time instead of adding to the old weights (otherwise every attempt would add Kahoot's 0.5 again)
    fresh = {row["kp_id"]: LOW_ACCURACY_WEIGHT if row["accuracy"] < LOW_ACCURACY else DEFAULT_WEIGHT
             for row in stats["by_kp"]}
    for kp in weak_kp_ids:
        fresh[kp] = fresh.get(kp, DEFAULT_WEIGHT) + KAHOOT_BONUS
    w.update(fresh)
    return {"class_id": stats["class_id"], "updated_at": now_iso(), "weights": w}


def refresh(lesson_id: str, quiz: dict) -> dict:
    """After every attempt, recompute this quiz's kp_stats and update weights.json for the next quiz (pipe step 7, plan_quiz.py)."""
    stats = kp_stats(quiz)
    alerts = outbox.load(lesson_id, "alerts") or {}
    weak = {r["kp_id"] for r in alerts.get("weak_from_reports", [])}
    new_weights = weights(stats, weak)
    for name, data in (("kp_stats", stats), ("weights", new_weights)):
        problems = errors(name, data)
        if problems:
            raise ValueError(f"{name}: {problems}")
    write_json(paths.kp_stats(quiz["quiz_id"]), stats)
    write_json(paths.WEIGHTS, new_weights)
    return stats
