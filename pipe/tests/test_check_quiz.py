import copy

import pytest

from check_quiz import check, main, normalize_answer, normalize_quote
from conftest import example

PLAN = {"n": 3, "allocation": {"KP03": 3}}


@pytest.fixture
def quiz():
    return example("quiz")


def run(quiz, plan=PLAN):
    return check(quiz, [example("segment")], example("coverage"), plan)


def test_examples_pass(quiz):
    errors, warnings = run(quiz)
    assert errors == [] and warnings == []


@pytest.mark.parametrize("given, expected", [
    (" Vues ", "vues"),
    ("VUES", "vues"),
    ("j’ai  vu", "j'ai vu"),
])
def test_normalize_answer_lenient(given, expected):
    assert normalize_answer(given) == expected


def test_normalize_answer_keeps_accents():
    assert normalize_answer("vûes") != normalize_answer("vues")


def test_normalize_quote_ignores_punctuation():
    assert normalize_quote("« Les pommes, que j’ai mangées ! »") == "les pommes que j'ai mangées"


def test_invented_quote_rejected(quiz):
    quiz["questions"][0]["source"]["quote"] = "les poires que j'ai mangées"
    errors, _ = run(quiz)
    assert any("not found" in e for e in errors)


def test_quote_with_different_punctuation_accepted(quiz):
    quiz["questions"][0]["source"]["quote"] = "Les pommes que j’ai mangées."
    assert run(quiz)[0] == []


def test_uncovered_point_rejected(quiz):
    quiz["questions"][0]["kp_id"] = "KP02"
    errors, _ = run(quiz, plan=None)
    assert any("KP02" in e and "was not taught" in e for e in errors)


def test_invented_frame_id_rejected(quiz):
    quiz["questions"][0]["source"]["frame_ids"] = [5531, 9999]
    errors, _ = run(quiz)
    assert any("9999" in e for e in errors)


def test_unknown_segment_rejected(quiz):
    quiz["questions"][0]["source"]["segment_id"] = "S-L-T1-20261017-1000-099"
    errors, _ = run(quiz)
    assert any("is not a segment of this lesson" in e for e in errors)


def test_mcq_answer_out_of_range(quiz):
    quiz["questions"][0]["answer"] = 4
    assert any("out of range" in e for e in run(quiz)[0])


def test_mcq_duplicate_choices(quiz):
    quiz["questions"][0]["choices"] = ["mangé", "Mangé", "mangés", "mangée"]
    assert any("duplicate choices" in e for e in run(quiz)[0])


def test_fill_blank_needs_blank_marker(quiz):
    quiz["questions"][1]["prompt"] = "Je les ai vues ?"
    assert any("___" in e for e in run(quiz)[0])


def test_allocation_mismatch(quiz):
    errors, _ = run(quiz, plan={"n": 5, "allocation": {"KP03": 5}})
    assert any("do not match" in e for e in errors)


def test_duplicate_q_ids_and_wrong_ids(quiz):
    quiz["questions"][1]["q_id"] = "Q1"
    quiz["quiz_id"] = "Q-other"
    errors, _ = run(quiz)
    assert any("is duplicated" in e for e in errors) and any("quiz_id" in e for e in errors)


def test_must_be_pending(quiz):
    quiz["status"] = "published"
    assert any("pending" in e for e in run(quiz)[0])


def test_segment_not_mapped_to_kp_is_only_a_warning(quiz):
    coverage = example("coverage")
    coverage["points"][2]["segment_ids"] = []
    errors, warnings = check(quiz, [example("segment")], coverage, PLAN)
    assert errors == [] and len(warnings) == 3


def test_cli(write_json, quiz):
    args = ["--quiz", str(write_json("quiz.json", quiz)),
            "--segments", str(write_json("segments.json", [example("segment")])),
            "--coverage", str(write_json("coverage.json", example("coverage"))),
            "--plan", str(write_json("plan.json", PLAN))]
    assert main(args) == 0
    bad = copy.deepcopy(quiz)
    bad["questions"][0]["answer"] = "1"  # an mcq answer must be an integer: the schema catches it first
    args[1] = str(write_json("bad.json", bad))
    assert main(args) == 1


def test_short_quote_is_a_warning(quiz):
    quiz["questions"][0]["source"]["quote"] = "j'ai mangées"
    errors, warnings = run(quiz)
    assert errors == [] and any("only 2 words" in w for w in warnings)


def test_overlong_quote_warned(quiz):
    """gen_quiz.md requires quotes of 5–25 words: an overly long quote is only a warning, not an error."""
    segment = example("segment")
    long_quote = " ".join(["on répète"] * 13)  # 26 words
    segment["speech"] += " " + long_quote
    quiz["questions"][0]["source"]["quote"] = long_quote
    errors, warnings = check(quiz, [segment], example("coverage"), PLAN)
    assert errors == [] and any("26 words, too long" in w for w in warnings)
