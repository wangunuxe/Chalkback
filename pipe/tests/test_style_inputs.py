import copy
import json
from datetime import datetime

import pytest

import extract_segments
from conftest import example
from fake_screenpipe import FakeScreenpipe, ocr
from style_inputs import collect

NOW = datetime.fromisoformat("2026-10-18T09:00:00+02:00")

ITEMS = [
    ocr(4410, "Question 1 : Complétez : Je les ai ___ (voir)", "2026-10-15T14:20:00+02:00", app="Chrome", window="Kahoot! | Create"),
    ocr(4411, "Question 1 : Complétez : Je les ai ___ (voir)", "2026-10-15T14:21:00+02:00", app="Chrome", window="Kahoot! | Create"),  # 同样文字
    ocr(4500, "Vrai ou faux : on accorde avec le sujet", "2026-10-10T08:15:00Z", app="Chrome", window="Quizlet - Set"),
    ocr(4600, "Formulaire sans titre - question à choix", "2026-10-12T19:00:00+02:00", app="Chrome", window="Quiz 4A - Google Forms"),
    ocr(4700, "Mail de la direction", "2026-10-15T15:00:00+02:00", app="Mail", window="Boîte de réception"),     # 不是出题平台
    ocr(4800, "Kahoot ancien", "2026-09-01T10:00:00+02:00", app="Chrome", window="Kahoot! | Create"),           # 超过 30 天
    {"type": "OCR", "content": {"frame_id": None, "text": "Quizlet sans frame", "timestamp": "2026-10-16T10:00:00+02:00",
                                "app_name": "Chrome", "window_name": "Quizlet"}},
]


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")


def edit(edit_id, at, action="edit", choices=None):
    e = copy.deepcopy(example("edit_event"))
    e.update(edit_id=edit_id, at=at, action=action)
    if choices:
        e["after"]["choices"] = choices
    return e


@pytest.fixture
def home(tmp_path):
    write(tmp_path / "config.json", example("config"))
    return tmp_path


@pytest.fixture
def screenpipe(monkeypatch):
    with FakeScreenpipe(ITEMS) as fake:
        monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", fake.url)
        yield fake


def with_profile(home):
    write(home / "state" / "style_profile.json", example("style_profile"))  # version 2, updated 2026-10-17T11:06


def with_edits(home, *edits):
    write(home / "state" / "edits.jsonl", "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in edits))


def test_first_run_collects_platform_screens(home, screenpipe):
    r = collect(home, NOW, 30, mock=False)
    assert r["needs_update"] and r["reason"] == "no_profile"
    assert r["next_version"] == 1 and r["current_profile"] is None and r["teacher_id"] == "T1"
    assert [(f["frame_id"], f["platform"]) for f in r["screen_history"]] == [
        (4411, "kahoot"), (4600, "google_forms"), (4500, "quizlet")]
    assert r["screen_history"][2]["timestamp"] == "2026-10-10T10:15:00+02:00"


def test_every_search_passes_explicit_window(home, screenpipe):
    collect(home, NOW, 30, mock=False)
    assert screenpipe.requests
    for req in screenpipe.requests:
        assert req["start_time"] == "2026-09-18T09:00:00+02:00" and req["end_time"] == "2026-10-18T09:00:00+02:00"
        assert req["content_type"] == "ocr" and req["window_name"]


def test_up_to_date_profile_skips_screenpipe(home, screenpipe):
    with_profile(home)
    with_edits(home, edit("E1", "2026-10-16T10:00:00+02:00"))
    assert collect(home, NOW, 30, mock=False) == {"needs_update": False, "reason": "up_to_date"}
    assert screenpipe.requests == []


def test_new_edits_trigger_update(home, screenpipe):
    with_profile(home)
    with_edits(home, edit("E1", "2026-10-16T10:00:00+02:00"),
               edit("E4", "2026-10-17T12:00:00+02:00", choices=["mangé", "mangées", "mangés", "mangeait"]),
               edit("E5", "2026-10-17T12:01:00+02:00", action="reject"))
    r = collect(home, NOW, 30, mock=False)
    assert r["reason"] == "new_edits" and r["next_version"] == 3
    assert [(e["edit_id"], e["changed"]) for e in r["edits"]] == [("E4", ["choices"]), ("E5", [])]
    # 已有风格文件时只看它之后的屏幕
    assert r["window"]["start"] == "2026-10-17T11:06:00+02:00"
    assert r["screen_history"] == []


def test_no_material_means_no_update(home):
    assert collect(home, NOW, 30, mock=True) == {"needs_update": False, "reason": "no_material", "search_error": None}


def test_mock_uses_edits_only(home, screenpipe):
    with_edits(home, edit("E1", "2026-10-16T10:00:00+02:00"))
    r = collect(home, NOW, 30, mock=True)
    assert r["needs_update"] and r["screen_history"] == [] and len(r["edits"]) == 1
    assert screenpipe.requests == []


def test_screenpipe_down_falls_back_to_edits(home, monkeypatch):
    monkeypatch.setattr(extract_segments, "SCREENPIPE_URL", "http://127.0.0.1:9")
    with_edits(home, edit("E1", "2026-10-16T10:00:00+02:00"))
    r = collect(home, NOW, 30, mock=False)
    assert r["needs_update"] and r["search_error"] and len(r["edits"]) == 1
