"""Review (A2, TC3): actions rewrite quiz.json, edits.jsonl follows the edit_event contract, the game exists only after publishing."""
import json

from .conftest import LESSON, QUIZ, read_jsonl


def quiz(home):
    return json.loads((home / "outbox" / LESSON / "quiz.json").read_text(encoding="utf-8"))


def act(client, **body):
    return client.post(f"/review/{LESSON}/action", json=body)


def test_every_edit_event_matches_contract(client, home, schema):
    act(client, action="approve", q_id="Q1")
    act(client, action="edit", q_id="Q2", changes={"answer": "vues", "prompt": "Je les ai ___ hier (voir)."})
    act(client, action="delete", q_id="Q3")
    edits = read_jsonl(home / "state" / "edits.jsonl")
    assert len(edits) == 4  # E3 from the seed data + three new ones
    for e in edits:
        schema("edit_event").validate(e)
    assert [e["edit_id"] for e in edits[1:]] == ["E4", "E5", "E6"]
    assert all(e["at"].endswith(("+02:00", "+01:00")) for e in edits[1:])


def test_edits_feed_pipe_style_learning(client, home):
    """pipe step 6 reads edits.jsonl: records written by the console must be processable by style_inputs.py."""
    import sys
    from .conftest import ROOT
    sys.path.insert(0, str(ROOT / "pipe" / "scripts"))
    from style_inputs import changed_fields, read_edits

    act(client, action="edit", q_id="Q1", changes={"choices": ["a", "b", "c", "d"]})
    edit = read_edits(home / "state" / "edits.jsonl")[-1]
    assert changed_fields(edit["before"], edit["after"]) == ["choices"]


def test_approve_keeps_quiz(client, home):
    before = quiz(home)
    event = act(client, action="approve", q_id="Q1").json()
    assert event["before"] == event["after"] == before["questions"][0]
    assert quiz(home) == before


def test_edit_rewrites_question_but_not_source(client, home):
    r = act(client, action="edit", q_id="Q1", changes={"prompt": "Nouvelle question ___ ?", "answer": 2})
    assert r.status_code == 200
    q1 = quiz(home)["questions"][0]
    assert q1["prompt"] == "Nouvelle question ___ ?" and q1["answer"] == 2
    assert q1["source"]["quote"] == "les pommes que j'ai mangées"
    assert act(client, action="edit", q_id="Q1", changes={"source": {"quote": "invented"}}).status_code == 422


def test_invalid_edit_is_rejected_and_quiz_untouched(client, home):
    before = quiz(home)
    assert act(client, action="edit", q_id="Q1", changes={"answer": "not an index"}).status_code == 422
    assert quiz(home) == before


def test_delete_and_reject_remove_question_but_not_the_last(client, home):
    assert act(client, action="delete", q_id="Q1").status_code == 200
    assert act(client, action="reject", q_id="Q2").status_code == 200
    assert [q["q_id"] for q in quiz(home)["questions"]] == ["Q3"]
    assert act(client, action="delete", q_id="Q3").status_code == 409


def test_unknown_action_or_question(client):
    assert act(client, action="bogus", q_id="Q1").status_code == 422
    assert act(client, action="approve", q_id="Q9").status_code == 404
    assert client.post("/review/L-T1-20990101-0000/action", json={"action": "approve", "q_id": "Q1"}).status_code == 404


def test_publish_rebuilds_game_with_reviewed_questions(client, home):
    act(client, action="edit", q_id="Q1", changes={"prompt": "Question relue ___ ?"})
    act(client, action="delete", q_id="Q3")
    r = client.post(f"/review/{LESSON}/publish")
    assert r.json() == {"status": "published", "play_url": f"/play/{QUIZ}"}
    html = (home / "outbox" / LESSON / "game.html").read_text(encoding="utf-8")
    assert "Question relue ___ ?" in html
    assert "Avec avoir, le participe" not in html  # the deleted Q3
    assert '"answer"' not in html and "les pommes que j'ai mangées" not in html
    assert quiz(home)["status"] == "published"
    assert act(client, action="approve", q_id="Q1").status_code == 409


def test_rejected_quiz_is_never_served(client):
    assert client.post(f"/review/{LESSON}/reject").json() == {"status": "rejected"}
    assert client.get(f"/play/{QUIZ}").status_code == 404
    assert client.post(f"/review/{LESSON}/publish").status_code == 409
