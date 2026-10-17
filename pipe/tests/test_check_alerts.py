import copy

import pytest

from check_alerts import check, main
from conftest import example

LOOKBACK = {
    "lesson_id": "L-T1-20261019-1000",
    "candidates": [
        {"kp_id": "KP01", "from_outbox": {"lesson_id": "L-T1-20261012-1000", "last_covered_at": "2026-10-12T10:20:00+02:00", "minutes": 6.0},
         "search_hits": [], "search_error": None},
        {"kp_id": "KP02", "from_outbox": None, "search_error": None,
         "search_hits": [{"content_type": "ocr", "id": 4410, "timestamp": "2026-10-14T20:30:00+02:00", "in_class_slot": False}]},
        {"kp_id": "KP04", "from_outbox": None, "search_error": None,
         "search_hits": [{"content_type": "audio", "id": 700, "timestamp": "2026-10-13T10:15:00+02:00", "in_class_slot": True}]},
    ],
}
REPORTS = [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]


@pytest.fixture
def alerts():
    return {
        "lesson_id": "L-T1-20261019-1000",
        "missed": [{"kp_id": "KP02", "note": "Mentionné hors cours, pas expliqué en classe."}],
        "covered_before": [{"kp_id": "KP01", "last_covered_at": "2026-10-12T10:20:00+02:00"},
                           {"kp_id": "KP04", "last_covered_at": "2026-10-13T10:15:00+02:00"}],
        "weak_from_reports": copy.deepcopy(REPORTS),
    }


def run(alerts):
    return check(alerts, LOOKBACK, REPORTS, example("syllabus"))


def test_correct_alerts_pass(alerts):
    assert run(alerts) == []


def test_missing_candidate(alerts):
    alerts["missed"] = []
    assert any("KP02" in e and "must" in e for e in run(alerts))


def test_candidate_in_both_lists(alerts):
    alerts["missed"].append({"kp_id": "KP01", "note": "x"})
    errors = run(alerts)
    assert any("KP01" in e and "more than once" in e for e in errors)
    assert any("KP01" in e and "outbox" in e for e in errors)


def test_covered_now_must_not_appear(alerts):
    alerts["missed"].append({"kp_id": "KP03", "note": "x"})
    assert any("KP03" in e for e in run(alerts))


def test_outbox_evidence_cannot_be_called_missed(alerts):
    alerts["covered_before"] = alerts["covered_before"][1:]
    alerts["missed"].append({"kp_id": "KP01", "note": "x"})
    assert any("should go into covered_before" in e for e in run(alerts))


def test_outbox_time_must_match(alerts):
    alerts["covered_before"][0]["last_covered_at"] = "2026-10-12T10:00:00+02:00"
    assert any("outbox record" in e for e in run(alerts))


def test_invented_time_rejected(alerts):
    alerts["covered_before"][1]["last_covered_at"] = "2026-10-15T10:15:00+02:00"
    assert any("does not match any look-back evidence" in e for e in run(alerts))


def test_same_instant_in_utc_accepted(alerts):
    alerts["covered_before"][1]["last_covered_at"] = "2026-10-13T08:15:00+00:00"
    assert run(alerts) == []


def test_weak_from_reports_must_come_from_reports(alerts):
    alerts["weak_from_reports"].append({"kp_id": "KP02", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"})
    assert any("read_reports" in e for e in run(alerts))


def test_cli(write_json, alerts):
    args = ["--alerts", str(write_json("alerts.json", alerts)), "--lookback", str(write_json("lookback.json", LOOKBACK)),
            "--reports", str(write_json("reports.json", REPORTS)), "--syllabus", str(write_json("syllabus.json", example("syllabus")))]
    assert main(args) == 0
    alerts["missed"][0]["note"] = 42  # the schema catches it first
    args[1] = str(write_json("bad.json", alerts))
    assert main(args) == 1
