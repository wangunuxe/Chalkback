"""check_coverage.py (TA3): coverage's segments, minutes and covered must all match the segments and the syllabus."""
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
    assert warnings == ["syllabus KP04 does not appear in points"]


def test_demo_data_is_consistent():
    assert run(*demo()) == ([], [])


def test_demo_lesson_plan_is_where_current_lesson_looks():
    from validate import validate_file
    plan = DEMO / "lesson_plans" / "4A" / "2026-10-17.json"
    assert validate_file("lesson_plan", plan) == []


@pytest.mark.parametrize("change,expected", [
    (lambda c: c["points"][2]["segment_ids"].append("S-L-T1-20261017-1000-009"), "is not a segment of this lesson"),
    (lambda c: c["points"][0].update(minutes=8.2), "minutes should be about 4.5"),
    (lambda c: c["points"][1].update(covered=True), "covered should be False"),
    (lambda c: c["points"].append({"kp_id": "KP99", "covered": False, "minutes": 0, "segment_ids": []}), "KP99 is not in the syllabus"),
    (lambda c: c["points"].append(copy.deepcopy(c["points"][0])), "KP01 appears 2 times"),
    (lambda c: c.update(class_id="4B"), "class_id"),
    (lambda c: c.update(syllabus_version=2), "syllabus should be fr-grammaire-4e v1"),
])
def test_errors(change, expected):
    coverage, segments = demo()
    change(coverage)
    errors, _ = run(coverage, segments)
    assert any(expected in e for e in errors), errors


def test_shared_segment_is_split_between_kps():
    coverage, segments = demo()
    # segment 002 (6 minutes) is recorded under both KP02 and KP03: 3 minutes each
    coverage["points"][1].update(covered=True, minutes=3.0, segment_ids=["S-L-T1-20261017-1000-002"])
    coverage["points"][2].update(minutes=3.0)
    assert run(coverage, segments) == ([], [])


def test_cli(tmp_path):
    lesson = tmp_path / "lesson.json"
    lesson.write_text(json.dumps(LESSON), encoding="utf-8")
    args = ["--coverage", str(DEMO / "coverage.json"), "--segments", str(DEMO / "segments.json"),
            "--syllabus", str(EXAMPLES / "syllabus.json"), "--lesson", str(lesson)]
    assert check_coverage.main(args) == 0
