"""extract_segments.py (TA2): split at slide changes into segments of about 2–5 minutes, microphone only, private windows filtered, all times in Europe/Paris."""
import json
import urllib.error
from datetime import datetime

import pytest

import extract_segments
from fake_screenpipe import FakeScreenpipe, audio, ocr, ui
from validate import validate_file

LESSON = "L-T1-20261017-1000"
START, END = "2026-10-17T10:00:00+02:00", "2026-10-17T11:00:00+02:00"

SLIDE_A = "Chapitre 3 : le passé composé avec avoir. Sujet + avoir + participe passé"
SLIDE_A_JITTER = "Chapitre 3 : le passé composé avec avoir. Sujet + avoir + participe passe"
SLIDE_B = "L'accord du participe passé avec le COD placé avant le verbe"
SLIDE_C = "Exercices : complétez avec le participe passé"


def t(hm: str, offset: str = "+02:00") -> str:
    return f"2026-10-17T{hm}{offset}"


@pytest.fixture
def run(monkeypatch):
    def _run(items, start=START, end=END):
        with FakeScreenpipe(items) as fake:
            monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", fake.url)
            return extract_segments.extract(LESSON, start, end), fake
    return _run


def minutes(seg):
    return (datetime.fromisoformat(seg["end"]) - datetime.fromisoformat(seg["start"])).total_seconds() / 60


def lesson_items():
    return [
        ocr(1, SLIDE_A, t("10:00:30")), ocr(2, SLIDE_A_JITTER, t("10:03:00")),
        ocr(3, SLIDE_B, t("10:08:00")),
        ocr(4, "Inbox — Réunion parents vendredi", t("10:09:00"), app="Google Chrome", window="Gmail - Inbox"),
        ocr(5, SLIDE_C, t("10:20:00")),
        audio(801, "Bonjour, aujourd'hui le passé composé avec avoir.", t("10:01:00")),
        audio(802, "Le participe passé ne s'accorde pas avec le sujet.", t("10:05:00")),
        audio(803, "Musique de la vidéo", t("10:06:00"), device_type="output"),
        audio(804, "Avec le COD placé avant, on accorde.", t("10:10:00")),
        audio(805, "Faites l'exercice numéro deux.", t("10:25:00")),
        audio(806, "On corrige ensemble.", t("10:41:00"), device_type="Input"),
    ]


def test_segments_follow_slides_and_contract(run, tmp_path):
    segments, _ = run(lesson_items())
    out = tmp_path / "segments.json"
    out.write_text(json.dumps(segments, ensure_ascii=False), encoding="utf-8")
    assert validate_file("segment", out) == []

    assert [s["segment_id"] for s in segments] == [f"S-{LESSON}-{i:03d}" for i in range(1, len(segments) + 1)]
    assert all(2 <= minutes(s) <= 5 for s in segments)
    assert all(s["start"].endswith("+02:00") and s["end"].endswith("+02:00") for s in segments)
    # slide jitter (SLIDE_A_JITTER) does not count as a slide change; both screenshots of the same slide are kept as evidence
    first = segments[0]
    assert first["start"] == START and first["slide_text"] == SLIDE_A and first["evidence"]["frame_ids"] == [1, 2]
    assert first["evidence"]["transcription_ids"] == [801]


def test_only_teacher_microphone(run):
    segments, _ = run(lesson_items())
    speech = " ".join(s["speech"] for s in segments)
    assert "Musique de la vidéo" not in speech       # sound played by the computer
    assert "On corrige ensemble." in speech           # device_type is case-insensitive


def test_private_windows_never_become_slide_text(run):
    segments, _ = run(lesson_items())
    assert all("Inbox" not in s["slide_text"] and "Réunion parents" not in s["slide_text"] for s in segments)
    assert all(4 not in s["evidence"]["frame_ids"] for s in segments)


def test_segments_without_speech_are_dropped(run):
    segments, _ = run(lesson_items())
    # slide A (8 minutes) splits into 2 segments, slide B (12 minutes) into 3, slide C (40 minutes) into 8, 13 in total;
    # only 10:01, 10:05, 10:10, 10:25, 10:41 have speech, the other segments without speech are not output
    assert len(segments) == 5
    assert all(s["speech"] for s in segments)


def test_quick_slide_flip_is_merged_and_other_apps_add_no_text(run):
    items = [
        ocr(1, SLIDE_A, t("10:00:10")),
        ocr(2, SLIDE_B, t("10:02:00")),                   # shown for only 30 seconds, same app: merged into the previous segment
        ocr(3, SLIDE_A, t("10:02:30")),
        ocr(4, "Wikipedia — participe passé", t("10:03:00"), app="Google Chrome", window="Wikipedia"),
        ocr(5, SLIDE_A, t("10:03:40")),
        audio(1, "On commence.", t("10:01:00")), audio(2, "Regardez.", t("10:03:10")),
    ]
    segments, _ = run(items, end="2026-10-17T10:05:00+02:00")
    assert len(segments) == 1
    seg = segments[0]
    assert seg["speech"] == "On commence. Regardez."
    assert SLIDE_B in seg["slide_text"] and "Wikipedia" not in seg["slide_text"]
    assert seg["app_name"] == "PowerPoint" and 4 not in seg["evidence"]["frame_ids"]


def test_no_screen_text_splits_lesson_by_five_minutes(run):
    segments, _ = run([audio(1, "Bonjour.", t("10:01:00")), audio(2, "Exercice.", t("10:12:00"))])
    assert [(s["start"][11:16], s["end"][11:16]) for s in segments] == [("10:00", "10:05"), ("10:10", "10:15")]
    assert all(s["slide_text"] == "" and s["app_name"] == "" and s["evidence"]["frame_ids"] == [] for s in segments)


def test_nothing_recorded_gives_empty_list(run, tmp_path, monkeypatch):
    with FakeScreenpipe([ocr(1, SLIDE_A, t("10:00:10"))]) as fake:
        monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", fake.url)
        out = tmp_path / "segments.json"
        assert extract_segments.main(["--lesson-id", LESSON, "--start", START, "--end", END, "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == []  # pipe step 2: no segments is treated as a failure


def test_utc_timestamps_become_paris_time(run):
    segments, _ = run([ocr(1, SLIDE_A, "2026-10-17T08:00:30Z"), audio(1, "Bonjour.", "2026-10-17T08:01:00Z")],
                      end="2026-10-17T10:04:00+02:00")
    assert segments[0]["start"] == START and segments[0]["end"] == "2026-10-17T10:04:00+02:00"


def test_accessibility_text_is_used(run):
    segments, fake = run([ui(SLIDE_C, t("10:00:20")), audio(1, "Exercice.", t("10:01:00"))],
                         end="2026-10-17T10:04:00+02:00")
    assert segments[0]["slide_text"] == SLIDE_C and segments[0]["app_name"] == "Keynote"
    assert segments[0]["evidence"]["frame_ids"] == []  # accessibility has no screenshots
    assert {r["content_type"] for r in fake.requests} == {"audio", "ocr", "accessibility"}


def test_old_screenpipe_without_accessibility(monkeypatch):
    def search(**params):
        if params["content_type"] == "accessibility":
            raise urllib.error.HTTPError("url", 400, "unknown content_type", {}, None)
        return {"data": [audio(1, "Bonjour.", t("10:01:00"))] if params["content_type"] == "audio" else []}
    monkeypatch.setattr(extract_segments, "search", search)
    assert len(extract_segments.extract(LESSON, START, "2026-10-17T10:04:00+02:00")) == 1


def test_pagination(run):
    items = [audio(i, f"Phrase {i}.", f"2026-10-17T10:{i // 60:02d}:{i % 60:02d}+02:00") for i in range(1, 250)]
    segments, fake = run(items, end="2026-10-17T10:05:00+02:00")
    assert sum(len(s["evidence"]["transcription_ids"]) for s in segments) == 249
    assert {r["offset"] for r in fake.requests if r["content_type"] == "audio"} == {"0", "100", "200"}


def test_mock_uses_this_lesson(tmp_path):
    out = tmp_path / "segments.json"
    extract_segments.main(["--lesson-id", "L-T1-20261019-1000", "--start", "2026-10-19T10:00:00+02:00",
                           "--end", "2026-10-19T11:00:00+02:00", "--out", str(out), "--mock"])
    [seg] = json.loads(out.read_text(encoding="utf-8"))
    assert seg["lesson_id"] == "L-T1-20261019-1000" and seg["segment_id"] == "S-L-T1-20261019-1000-003"
    assert seg["start"] == "2026-10-19T10:12:05+02:00" and seg["end"] == "2026-10-19T10:16:40+02:00"
    assert validate_file("segment", out) == []
