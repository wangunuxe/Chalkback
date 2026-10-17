"""TB4 acceptance scenario: tell "not taught" apart from "taught last week".

This lesson: 2026-10-19 (Monday) 10:00–11:00, 4A. The lesson plan covers KP01–KP04; only KP03 was taught in this lesson.
- KP01: last Monday's (10-12) lesson for this class was already processed and the outbox records it as taught → reliable evidence
- KP02: taught to another class (4B) and taught 25 days ago (outside the window), neither counts; it only appeared on screen during evening lesson prep → only hits that do not count
- KP04: the teacher said it aloud during last Tuesday's (10-13) class slot (time in UTC format) → candidate evidence
"""
import json

import pytest

import extract_segments
from conftest import example
from fake_screenpipe import FakeScreenpipe, audio, ocr
from lookback import lookback

SYLLABUS = example("syllabus")
TIMETABLE = [
    {"day": "MON", "start": "10:00", "end": "11:00", "class_id": "4A"},
    {"day": "TUE", "start": "10:00", "end": "11:00", "class_id": "4A"},
    {"day": "TUE", "start": "14:00", "end": "15:00", "class_id": "4B"},
]
LESSON_ID = "L-T1-20261019-1000"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def past_lesson(home, lesson_id, class_id, kp_id, seg_start=None):
    d = home / "outbox" / lesson_id
    seg_id = f"S-{lesson_id}-001"
    write(d / "coverage.json", {"lesson_id": lesson_id, "class_id": class_id,
                                "points": [{"kp_id": kp_id, "covered": True, "minutes": 6.0, "segment_ids": [seg_id]}]})
    if seg_start:
        write(d / "segments.json", [{"segment_id": seg_id, "start": seg_start}])


@pytest.fixture
def home(tmp_path):
    plan = tmp_path / "lesson_plans" / "4A" / "2026-10-19.json"
    write(plan, {"class_id": "4A", "date": "2026-10-19", "syllabus_id": "fr-grammaire-4e", "kp_ids": ["KP01", "KP02", "KP03", "KP04"]})
    past_lesson(tmp_path, "L-T1-20261012-1000", "4A", "KP01", seg_start="2026-10-12T10:20:00+02:00")
    past_lesson(tmp_path, "L-T1-20261013-1400", "4B", "KP02")      # a different class
    past_lesson(tmp_path, "L-T1-20260924-1000", "4A", "KP02")      # older than 21 days
    return tmp_path


@pytest.fixture
def lesson(home):
    return {"lesson_id": LESSON_ID, "class_id": "4A", "start": "2026-10-19T10:00:00+02:00",
            "end": "2026-10-19T11:00:00+02:00", "lesson_plan": str(home / "lesson_plans" / "4A" / "2026-10-19.json")}


@pytest.fixture
def coverage():
    c = example("coverage")
    c["lesson_id"] = LESSON_ID
    return c


ITEMS = [
    ocr(4410, "Le passé composé avec être : je suis allé, elle est venue", "2026-10-14T20:30:00+02:00"),
    audio(700, "Aujourd'hui on voit l'imparfait, le temps de la description dans le passé", "2026-10-13T08:15:00Z"),
    audio(701, "imparfait", "2026-10-13T10:20:00+02:00", device_type="output"),   # sound played by the computer
    audio(900, "On reverra le passé composé avec être demain", "2026-10-19T10:30:00+02:00"),  # inside this lesson, does not count as look-back
]


@pytest.fixture
def screenpipe(monkeypatch):
    with FakeScreenpipe(ITEMS) as fake:
        monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", fake.url)
        yield fake


def run(lesson, coverage, home, mock=False):
    return lookback(lesson, coverage, SYLLABUS, {"timetable": TIMETABLE}, home, days=21, mock=mock)


def by_kp(result):
    return {c["kp_id"]: c for c in result["candidates"]}


def test_candidates_are_planned_but_not_covered(lesson, coverage, home, screenpipe):
    result = run(lesson, coverage, home)
    assert result["planned"] == ["KP01", "KP02", "KP03", "KP04"]
    assert result["covered_now"] == ["KP03"]
    assert list(by_kp(result)) == ["KP01", "KP02", "KP04"]
    assert result["window"] == {"start": "2026-09-28T10:00:00+02:00", "end": "2026-10-19T10:00:00+02:00"}


def test_outbox_of_same_class_is_reliable_evidence(lesson, coverage, home, screenpipe):
    kp01 = by_kp(run(lesson, coverage, home))["KP01"]
    assert kp01["from_outbox"] == {"lesson_id": "L-T1-20261012-1000", "last_covered_at": "2026-10-12T10:20:00+02:00", "minutes": 6.0}
    assert kp01["search_hits"] == []
    # KP01 has reliable evidence so there is no search ("avoir" is a keyword unique to KP01)
    assert not any(r.get("q") == "avoir" for r in screenpipe.requests)


def test_other_class_and_old_lessons_ignored(lesson, coverage, home, screenpipe):
    kp02 = by_kp(run(lesson, coverage, home))["KP02"]
    assert kp02["from_outbox"] is None
    assert [(h["content_type"], h["id"], h["in_class_slot"]) for h in kp02["search_hits"]] == [("ocr", 4410, False)]


def test_audio_in_class_slot_found_and_converted_to_paris(lesson, coverage, home, screenpipe):
    hits = by_kp(run(lesson, coverage, home))["KP04"]["search_hits"]
    assert [(h["id"], h["timestamp"], h["in_class_slot"]) for h in hits] == [(700, "2026-10-13T10:15:00+02:00", True)]


def test_every_search_passes_explicit_window(lesson, coverage, home, screenpipe):
    run(lesson, coverage, home)
    assert screenpipe.requests
    for r in screenpipe.requests:
        assert r["start_time"] == "2026-09-28T10:00:00+02:00"
        assert r["end_time"] == "2026-10-19T10:00:00+02:00"


def test_mock_skips_screenpipe(lesson, coverage, home, screenpipe):
    result = run(lesson, coverage, home, mock=True)
    assert screenpipe.requests == []
    assert by_kp(result)["KP01"]["from_outbox"] is not None
    assert by_kp(result)["KP01"]["search_error"] is None            # reliable evidence, no search needed
    assert "mock" in by_kp(result)["KP02"]["search_error"]          # if we did not search, say so


def test_screenpipe_down_is_recorded_not_raised(lesson, coverage, home, monkeypatch):
    monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", "http://127.0.0.1:9")
    kp02 = by_kp(run(lesson, coverage, home))["KP02"]
    assert kp02["search_error"] and kp02["search_hits"] == []


def test_no_lesson_plan(lesson, coverage, home, screenpipe):
    lesson["lesson_plan"] = None
    result = run(lesson, coverage, home)
    assert result["has_lesson_plan"] is False and result["candidates"] == []


def test_microphone_check_ignores_case(lesson, coverage, home, monkeypatch):
    """screenpipe's device_type may be "Input" (pending testing in TA1): a different case still counts as the teacher's microphone."""
    items = [audio(702, "L'imparfait sert à décrire", "2026-10-13T10:25:00+02:00", device_type="Input"),
             audio(703, "imparfait", "2026-10-13T10:26:00+02:00", device_type="Output")]
    with FakeScreenpipe(items) as fake:
        monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", fake.url)
        hits = by_kp(run(lesson, coverage, home))["KP04"]["search_hits"]
    assert [h["id"] for h in hits] == [702]
