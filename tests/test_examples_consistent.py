"""contracts/examples/ 是全员共用的一套 mock：每个文件单独合法还不够，彼此之间也必须对得上。

改其中一个示例时，必须同时改所有引用它的示例（技术文档 §0：改契约需全员同意）。
真实的演示数据请放在 demo/，不要放在这里。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts" / "examples"
HINT = "contracts/examples 必须整套一致；演示数据请放 demo/"


@pytest.fixture(scope="module")
def ex():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in EXAMPLES.glob("*.json")}


def test_same_lesson_everywhere(ex):
    lesson = ex["coverage"]["lesson_id"]
    for name in ("segment", "quiz", "alerts", "coverage_share"):
        assert ex[name]["lesson_id"] == lesson, f"{name}.lesson_id ≠ coverage.lesson_id；{HINT}"
    assert ex["quiz"]["quiz_id"] == f"Q-{lesson}"
    for name in ("edit_event", "attempt", "kp_stats"):
        assert ex[name]["quiz_id"] == ex["quiz"]["quiz_id"], f"{name}.quiz_id ≠ quiz.quiz_id；{HINT}"


def test_segment_references_exist(ex):
    known = {ex["segment"]["segment_id"]}
    for p in ex["coverage"]["points"]:
        assert set(p["segment_ids"]) <= known, f"coverage 引用了示例里没有的片段 {set(p['segment_ids']) - known}；{HINT}"
    for q in ex["quiz"]["questions"]:
        assert q["source"]["segment_id"] in known, f"quiz {q['q_id']} 引用了示例里没有的片段；{HINT}"


def test_coverage_share_is_coverage_without_private_fields(ex):
    cov, share = ex["coverage"], ex["coverage_share"]
    assert share["points"] == [{k: p[k] for k in ("kp_id", "covered", "minutes")} for p in cov["points"]], HINT


def test_knowledge_points_exist_in_syllabus(ex):
    kps = {kp["kp_id"] for kp in ex["syllabus"]["knowledge_points"]}
    used = (
        {p["kp_id"] for p in ex["coverage"]["points"]}
        | {q["kp_id"] for q in ex["quiz"]["questions"]}
        | set(ex["lesson_plan"]["kp_ids"])
        | set(ex["weights"]["weights"])
        | {a["kp_id"] for key in ("missed", "covered_before", "weak_from_reports") for a in ex["alerts"][key]}
    )
    assert used <= kps, f"这些知识点不在 syllabus 示例里：{used - kps}"


def test_quiz_example_passes_check_quiz(ex, tmp_path):
    """B 的语义检查（只考讲过的点、原话来自转写）对示例也必须成立。"""
    files = {}
    for name, data in (("quiz", ex["quiz"]), ("segments", [ex["segment"]]), ("coverage", ex["coverage"])):
        files[name] = tmp_path / f"{name}.json"
        files[name].write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "pipe" / "scripts" / "check_quiz.py"),
                        "--quiz", str(files["quiz"]), "--segments", str(files["segments"]),
                        "--coverage", str(files["coverage"])], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + HINT
