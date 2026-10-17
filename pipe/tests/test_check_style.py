import copy

import pytest

from check_style import check, main
from conftest import example

OLD = example("style_profile")  # version 2: frame 4410 @ 2026-10-15T14:20, edit E3

INPUTS = {
    "needs_update": True, "reason": "new_edits", "teacher_id": "T1", "now": "2026-10-18T09:00:00+02:00",
    "next_version": 3, "current_profile": OLD,
    "screen_history": [{"frame_id": 4600, "timestamp": "2026-10-17T19:00:00+02:00", "platform": "google_forms",
                        "window_name": "Quiz 4A - Google Forms", "text": "…"}],
    "edits": [{"edit_id": "E4", "action": "edit", "changed": ["prompt"]}],
}


@pytest.fixture
def profile():
    return {
        "teacher_id": "T1", "version": 3, "updated_at": "2026-10-18T09:00:00+02:00",
        "rules": [
            # keep the old rules and old evidence
            copy.deepcopy(OLD["rules"][0]),
            copy.deepcopy(OLD["rules"][1]),
            {"rule": "Énoncés courts, une seule phrase", "origin": "teacher_edit", "evidence": {"edit_ids": ["E4"]}},
            {"rule": "Une question par concept sur Forms", "origin": "screen_history",
             "evidence": {"frame_ids": [4600], "timestamp": "2026-10-17T19:00:00+02:00"}},
        ],
    }


def test_valid_profile_passes(profile):
    assert check(profile, INPUTS) == []


def test_version_and_updated_at_must_follow_inputs(profile):
    profile["version"] = 2
    profile["updated_at"] = "2026-10-18T08:00:00+02:00"
    errors = check(profile, INPUTS)
    assert any("version" in e for e in errors) and any("updated_at" in e for e in errors)


def test_wrong_teacher(profile):
    profile["teacher_id"] = "T2"
    assert any("teacher_id" in e for e in check(profile, INPUTS))


def test_invented_frame_rejected(profile):
    profile["rules"][3]["evidence"]["frame_ids"] = [9999]
    assert any("9999" in e for e in check(profile, INPUTS))


def test_timestamp_must_belong_to_cited_frame(profile):
    profile["rules"][3]["evidence"]["timestamp"] = "2026-10-15T14:20:00+02:00"   # that is 4410's time
    assert any("timestamp" in e for e in check(profile, INPUTS))


def test_screen_rule_needs_timestamp(profile):
    del profile["rules"][3]["evidence"]["timestamp"]
    assert any("timestamp" in e for e in check(profile, INPUTS))


def test_invented_edit_rejected(profile):
    profile["rules"][2]["evidence"]["edit_ids"] = ["E99"]
    assert any("E99" in e for e in check(profile, INPUTS))


def test_wrong_evidence_kind(profile):
    profile["rules"][2]["evidence"] = {"frame_ids": [4600], "timestamp": "2026-10-17T19:00:00+02:00"}
    assert any("edit_ids" in e for e in check(profile, INPUTS))


def test_duplicate_rules(profile):
    profile["rules"][2]["rule"] = "  énoncés courts,  une seule phrase "
    profile["rules"][3]["rule"] = "Énoncés courts, une seule phrase"
    assert any("is duplicated" in e for e in check(profile, INPUTS))


def test_empty_rules(profile):
    profile["rules"] = []
    assert any("at least one rule" in e for e in check(profile, INPUTS))


def test_cli(write_json, profile):
    args = ["--profile", str(write_json("p.json", profile)), "--inputs", str(write_json("i.json", INPUTS))]
    assert main(args) == 0
    profile["rules"][0]["origin"] = "guess"   # the schema catches it first
    args[1] = str(write_json("bad.json", profile))
    assert main(args) == 1
