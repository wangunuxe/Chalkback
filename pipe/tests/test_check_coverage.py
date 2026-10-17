"""check_coverage.py（TA3）：coverage 的片段、分钟数、covered 都要和片段与考纲对得上。"""
import copy
import json

import pytest

import check_coverage
from conftest import EXAMPLES, ROOT, example

DEMO = ROOT / "demo"
LESSON = {"lesson_id": "L-T1-20261017-1000", "teacher_id": "T1", "class_id": "4A"}


def run(coverage, segments, syllabus=None):
    return check_coverage.check(coverage, segments, syllabus or example("syllabus"), LESSON)


def demo():
    load = lambda name: json.loads((DEMO / name).read_text(encoding="utf-8"))  # noqa: E731
    return load("coverage.json"), load("segments.json")


def test_contract_example_passes_with_warning_for_unlisted_kp():
    errors, warnings = run(example("coverage"), [example("segment")])
    assert errors == []
    assert warnings == ["考纲的 KP04 没有出现在 points 里"]


def test_demo_data_is_consistent():
    assert run(*demo()) == ([], [])


def test_demo_lesson_plan_is_where_current_lesson_looks():
    from validate import validate_file
    plan = DEMO / "lesson_plans" / "4A" / "2026-10-17.json"
    assert validate_file("lesson_plan", plan) == []


@pytest.mark.parametrize("change,expected", [
    (lambda c: c["points"][2]["segment_ids"].append("S-L-T1-20261017-1000-009"), "不是本节的片段"),
    (lambda c: c["points"][0].update(minutes=8.2), "minutes 应约为 4.5"),
    (lambda c: c["points"][1].update(covered=True), "covered 应为 False"),
    (lambda c: c["points"].append({"kp_id": "KP99", "covered": False, "minutes": 0, "segment_ids": []}), "KP99 不在考纲里"),
    (lambda c: c["points"].append(copy.deepcopy(c["points"][0])), "KP01 出现了 2 次"),
    (lambda c: c.update(class_id="4B"), "class_id"),
    (lambda c: c.update(syllabus_version=2), "考纲应为 fr-grammaire-4e v1"),
])
def test_errors(change, expected):
    coverage, segments = demo()
    change(coverage)
    errors, _ = run(coverage, segments)
    assert any(expected in e for e in errors), errors


def test_shared_segment_is_split_between_kps():
    coverage, segments = demo()
    # 片段 002（6 分钟）同时记在 KP02 和 KP03 下：各 3 分钟
    coverage["points"][1].update(covered=True, minutes=3.0, segment_ids=["S-L-T1-20261017-1000-002"])
    coverage["points"][2].update(minutes=3.0)
    assert run(coverage, segments) == ([], [])


def test_cli(tmp_path):
    lesson = tmp_path / "lesson.json"
    lesson.write_text(json.dumps(LESSON), encoding="utf-8")
    args = ["--coverage", str(DEMO / "coverage.json"), "--segments", str(DEMO / "segments.json"),
            "--syllabus", str(EXAMPLES / "syllabus.json"), "--lesson", str(lesson)]
    assert check_coverage.main(args) == 0
