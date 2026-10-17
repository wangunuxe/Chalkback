"""read_reports.py (TA5): read weak points only from real Kahoot report pages; output [] when nothing is found or on error, never invent."""
import json
from datetime import datetime

import pytest

import extract_segments
import read_reports
from conftest import EXAMPLES
from fake_screenpipe import FakeScreenpipe, ocr

NOW = datetime.fromisoformat("2026-10-17T12:00:00+02:00")
SYLLABUS = EXAMPLES / "syllabus.json"


def report(frame_id, text, ts="2026-10-16T18:02:00+02:00", window="Kahoot! | Reports - Chrome"):
    return ocr(frame_id, text, ts, app="Google Chrome", window=window)


@pytest.fixture
def weak(monkeypatch):
    def _weak(items):
        with FakeScreenpipe(items) as fake:
            monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", fake.url)
            return read_reports.read_reports(7, read_reports.load_kps(SYLLABUS), now=NOW), fake
    return _weak


def test_low_accuracy_question_maps_to_its_kp(weak):
    result, fake = weak([report(1, "Question 3\nL'accord du participe passé avec le COD\n23% correct\nQuestion 4\nLe passé composé avec avoir\n91% correct")])
    assert result == [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]
    assert {r["window_name"] for r in fake.requests} == {"kahoot"}  # search by window title, not full-text search


def test_header_marks_following_questions(weak):
    result, _ = weak([report(1, "Difficult questions\nL'imparfait de description\nAll questions")])
    assert [r["kp_id"] for r in result] == ["KP04"]


def test_ambiguous_question_is_skipped(weak):
    # "passé composé" is a keyword of both KP01 and KP02, a tied score: when unsure, do not tag
    result, _ = weak([report(1, "Le passé composé\n31% correct")])
    assert result == []


def test_no_naive_number_matching(weak):
    # "correct: 1" used to match "correct: 10"; "cod" must not match "code"
    result, _ = weak([report(1, "Participe passé et accord\ncorrect: 10 / 12\n85%"), report(2, "Code de la route\n10%")])
    assert result == []


def test_only_kahoot_windows_and_latest_time(weak):
    result, _ = weak([
        report(1, "Accord du participe passé avec le COD\n20%", ts="2026-10-15T09:00:00+02:00"),
        report(2, "Accord du participe passé avec le COD\n35%", ts="2026-10-16T08:00:00Z"),
        report(3, "Accord du participe passé avec le COD\n10%", window="Mes notes"),
    ])
    assert result == [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T10:00:00+02:00"}]


def test_no_report_found_is_empty_not_invented(weak):
    result, _ = weak([])
    assert result == []


def cli(tmp_path, *extra):
    out = tmp_path / "reports.json"
    code = read_reports.main(["--syllabus", str(SYLLABUS), "--out", str(out), *extra])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_screenpipe_down_writes_empty_and_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", "http://127.0.0.1:9")
    assert cli(tmp_path) == (1, [])
    assert "failed" in capsys.readouterr().err


def test_missing_syllabus_writes_empty_and_fails(tmp_path):
    out = tmp_path / "reports.json"
    assert read_reports.main(["--syllabus", str(tmp_path / "nope.json"), "--out", str(out)]) == 1
    assert json.loads(out.read_text(encoding="utf-8")) == []


def test_mock(tmp_path):
    alerts = json.loads((EXAMPLES / "alerts.json").read_text(encoding="utf-8"))
    assert cli(tmp_path, "--mock") == (0, alerts["weak_from_reports"])
