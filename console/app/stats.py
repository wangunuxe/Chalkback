"""判分（TC4）和学情统计（TC5）：attempts.jsonl → kp_stats → weights.json（§5）。

权重规则（§5 weights）：默认 1.0；该知识点正确率低于 50% 设为 2.0；来自 Kahoot 报告的薄弱点再加 0.5。
weights.json 只保存一个班级（plan_quiz.py 只用 class_id 相同的权重）：同班合并更新，换班就重写。
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
    """超时（response 为 None）一律算错。"""
    if response is None:
        return False
    answer, kind = question["answer"], question["type"]
    if kind == "mcq":
        # bool 是 int 的子类：True 不能当作下标 1
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
    # 每次都从规则重新算，不在旧权重上累加（否则每次作答都会再加一次 Kahoot 的 0.5）
    fresh = {row["kp_id"]: LOW_ACCURACY_WEIGHT if row["accuracy"] < LOW_ACCURACY else DEFAULT_WEIGHT
             for row in stats["by_kp"]}
    for kp in weak_kp_ids:
        fresh[kp] = fresh.get(kp, DEFAULT_WEIGHT) + KAHOOT_BONUS
    w.update(fresh)
    return {"class_id": stats["class_id"], "updated_at": now_iso(), "weights": w}


def refresh(lesson_id: str, quiz: dict) -> dict:
    """每次作答后重算本测验的 kp_stats，并更新 weights.json，下次出题使用（pipe 第 7 步 plan_quiz.py）。"""
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
