"""Student game (TC4) and learning statistics (TC5)."""
import json

import pytest

from .conftest import LESSON, QUIZ, read_jsonl


@pytest.fixture
def published(client):
    assert client.post(f"/review/{LESSON}/publish").status_code == 200
    return client


def answer(client, q_id, response, nickname="lapin", time_ms=5000):
    return client.post(f"/play/{QUIZ}/attempt", json={"nickname": nickname, "q_id": q_id, "response": response, "time_ms": time_ms})


def test_unpublished_or_unknown_quiz_is_404(client):
    assert client.get(f"/play/{QUIZ}").status_code == 404  # the seed quiz is pending, not reviewed yet
    assert answer(client, "Q1", 1).status_code == 404
    assert client.get("/play/Q-L-T1-20990101-0000").status_code == 404
    assert client.post("/play/Q-L-T1-20990101-0000/attempt", json={"nickname": "a", "q_id": "Q1", "response": 1}).status_code == 404


def test_published_game_is_served(published):
    r = published.get(f"/play/{QUIZ}")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("q_id,response,correct", [
    ("Q1", 1, True), ("Q1", 0, False), ("Q1", True, False),        # mcq: True must not be treated as index 1
    ("Q2", "  VUES ", True), ("Q2", "vus", False),                  # fill_blank: ignores case and whitespace
    ("Q3", False, True), ("Q3", 0, False),                          # true_false: only booleans accepted
    ("Q1", None, False), ("Q2", None, False), ("Q3", None, False),  # a timeout always counts as wrong
])
def test_grading(published, q_id, response, correct):
    r = answer(published, q_id, response)
    assert r.status_code == 200 and r.json()["correct"] is correct


def test_unknown_question_is_404(published):
    assert answer(published, "Q9", 1).status_code == 404


def test_attempts_follow_contract(published, home, schema):
    answer(published, "Q1", 1)
    answer(published, "Q2", "vues", nickname="renard")
    rows = read_jsonl(home / "state" / "attempts.jsonl")[1:]  # the first row is seed data
    assert [r["nickname"] for r in rows] == ["lapin", "renard"]
    for r in rows:
        schema("attempt").validate(r)
        assert r["at"].endswith(("+02:00", "+01:00"))


def test_stats_and_weights(published, home, schema):
    # The seed data already has lapin42 getting Q1 wrong. Three more students: only 2 of the 7 KP03 attempts are correct
    answer(published, "Q1", 1, nickname="a")
    answer(published, "Q2", "vus", nickname="b")
    answer(published, "Q3", True, nickname="c")
    answer(published, "Q1", 0, nickname="c")
    answer(published, "Q2", "vues", nickname="a")
    answer(published, "Q3", True, nickname="b")

    stats = json.loads((home / "state" / "kp_stats" / f"{QUIZ}.json").read_text(encoding="utf-8"))
    schema("kp_stats").validate(stats)
    assert stats["n_players"] == 4
    assert stats["by_kp"][0]["kp_id"] == "KP03" and stats["by_kp"][0]["accuracy"] == pytest.approx(2 / 7, abs=1e-3)

    weights = json.loads((home / "state" / "weights.json").read_text(encoding="utf-8"))
    schema("weights").validate(weights)
    # accuracy < 50% -> 2.0; KP03 is a Kahoot weak point in alerts -> +0.5. Repeated attempts do not accumulate
    assert weights["class_id"] == "4A" and weights["weights"]["KP03"] == 2.5

    detail = published.get(f"/review/{LESSON}").json()
    assert detail["kp_stats"] == stats


def test_good_results_reset_weight(published, home):
    for nickname in "abcdefgh":
        answer(published, "Q1", 1, nickname=nickname)
    weights = json.loads((home / "state" / "weights.json").read_text(encoding="utf-8"))
    assert weights["weights"]["KP03"] == 1.5  # accuracy 8/9 -> 1.0, Kahoot weak point +0.5
