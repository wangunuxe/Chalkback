import json

import pytest

import current_lesson
from conftest import example

# 2026-10-19 是周一；10 月 25 日凌晨夏令时结束（+02:00 → +01:00）
TIMETABLE = [
    {"day": "MON", "start": "10:00", "end": "11:00", "class_id": "4A"},
    {"day": "MON", "start": "14:00", "end": "15:00", "class_id": "4B"},
    {"day": "TUE", "start": "14:00", "end": "15:00", "class_id": "5B"},
]


@pytest.fixture
def home(tmp_path, monkeypatch):
    config = example("config") | {"timetable": TIMETABLE}
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("CHALKBACK_HOME", str(tmp_path))
    return tmp_path


def run(capsys, *args):
    code = current_lesson.main(list(args))
    out = capsys.readouterr().out
    return code, (json.loads(out) if code == 0 else None)


def test_just_ended(home, capsys):
    code, lesson = run(capsys, "--now", "2026-10-19T11:05:00+02:00")
    assert code == 0
    assert lesson["lesson_id"] == "L-T1-20261019-1000"
    assert lesson["class_id"] == "4A"
    assert lesson["start"] == "2026-10-19T10:00:00+02:00"
    assert lesson["end"] == "2026-10-19T11:00:00+02:00"
    assert lesson["ready"] is False and lesson["lesson_plan"] is None


def test_picks_latest_ended_slot_of_the_day(home, capsys):
    _, lesson = run(capsys, "--now", "2026-10-19T16:00:00+02:00")
    assert lesson["lesson_id"] == "L-T1-20261019-1400"
    assert lesson["class_id"] == "4B"


def test_lesson_in_progress_is_skipped(home, capsys):
    # 周一 10:30，第一节还没结束 → 回到上周二
    _, lesson = run(capsys, "--now", "2026-10-19T10:30:00+02:00")
    assert lesson["lesson_id"] == "L-T1-20261013-1400"


def test_weekend_goes_back(home, capsys):
    _, lesson = run(capsys, "--now", "2026-10-18T09:00:00+02:00")
    assert lesson["lesson_id"] == "L-T1-20261013-1400"


def test_across_dst_change(home, capsys):
    # 现在是冬令时，上一节课在夏令时：课表时间按当天的巴黎时间算
    _, lesson = run(capsys, "--now", "2026-10-26T09:00:00+01:00")
    assert lesson["lesson_id"] == "L-T1-20261020-1400"
    assert lesson["start"] == "2026-10-20T14:00:00+02:00"


def test_utc_input_is_converted_to_paris(home, capsys):
    _, lesson = run(capsys, "--now", "2026-10-19T09:05:00+00:00")  # = 11:05 巴黎
    assert lesson["lesson_id"] == "L-T1-20261019-1000"


def test_ready_and_lesson_plan_detected(home, capsys):
    (home / "outbox" / "L-T1-20261019-1000").mkdir(parents=True)
    (home / "outbox" / "L-T1-20261019-1000" / "ready").touch()
    (home / "lesson_plans" / "4A").mkdir(parents=True)
    (home / "lesson_plans" / "4A" / "2026-10-19.json").write_text("{}")
    _, lesson = run(capsys, "--now", "2026-10-19T11:05:00+02:00")
    assert lesson["ready"] is True
    assert lesson["lesson_plan"].endswith("2026-10-19.json")


def test_no_lesson_in_window(home, capsys):
    code, _ = run(capsys, "--now", "2026-10-18T09:00:00+02:00", "--days", "2")
    assert code == 2


def test_naive_now_rejected(home):
    with pytest.raises(SystemExit):
        current_lesson.main(["--now", "2026-10-19T11:05:00"])
