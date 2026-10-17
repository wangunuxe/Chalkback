import json

from plan_quiz import allocate, main, scores_from
from conftest import example


def test_single_point_gets_all_questions():
    assert allocate({"KP03": 4.5}, 5) == {"KP03": 5}


def test_every_point_gets_one_then_largest_remainder():
    # the remaining 3 questions split 3:1 → 2.25 / 0.75 → integer parts 2 / 0, the larger remainder (0.75) takes the last question
    assert allocate({"A": 3.0, "B": 1.0}, 5) == {"A": 3, "B": 2}


def test_more_points_than_questions_takes_top_scores():
    assert allocate({"A": 1, "B": 5, "C": 3, "D": 2}, 2) == {"B": 1, "C": 1}


def test_ties_are_deterministic():
    assert allocate({"B": 1, "A": 1, "C": 1}, 2) == {"A": 1, "B": 1}


def test_zero_minutes_split_evenly():
    assert allocate({"A": 0, "B": 0}, 4) == {"A": 2, "B": 2}


def test_total_always_n():
    scores = {"A": 7.3, "B": 2.2, "C": 0.4}
    for n in range(3, 12):
        assert sum(allocate(scores, n).values()) == n


def test_only_covered_points_and_weights_applied():
    coverage = example("coverage")
    coverage["points"].append({"kp_id": "KP04", "covered": True, "minutes": 3.0, "segment_ids": []})
    weights = {"class_id": "4A", "updated_at": "2026-10-17T12:00:00+02:00", "weights": {"KP03": 2.0}}
    assert scores_from(coverage, weights) == {"KP03": 9.0, "KP04": 3.0}


def test_weights_for_other_class_ignored():
    weights = {"class_id": "5B", "updated_at": "2026-10-17T12:00:00+02:00", "weights": {"KP03": 2.0}}
    assert scores_from(example("coverage"), weights) == {"KP03": 4.5}


def test_cli_with_examples(write_json, capsys):
    code = main(["--coverage", str(write_json("coverage.json", example("coverage"))),
                 "--weights", str(write_json("weights.json", example("weights")))])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["allocation"] == {"KP03": 5}


def test_cli_missing_weights_file_is_fine(write_json, tmp_path, capsys):
    code = main(["--coverage", str(write_json("coverage.json", example("coverage"))),
                 "--weights", str(tmp_path / "nope.json")])
    assert code == 0


def test_cli_nothing_covered_exits_2(write_json, capsys):
    coverage = example("coverage")
    for p in coverage["points"]:
        p["covered"] = False
    assert main(["--coverage", str(write_json("coverage.json", coverage))]) == 2
