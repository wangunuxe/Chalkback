import json
import subprocess
import sys

import pytest

import doctor
from conftest import PIPE, ROOT, example
from fake_screenpipe import FakeScreenpipe


@pytest.fixture
def home(tmp_path, monkeypatch):
    subprocess.run([sys.executable, str(ROOT / "tools" / "seed_mock_home.py"), "--home", str(tmp_path)], check=True,
                   capture_output=True)
    monkeypatch.setenv("CHALKBACK_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def screenpipe(monkeypatch):
    with FakeScreenpipe([]) as fake:
        monkeypatch.setenv("SCREENPIPE_URL", fake.url)
        yield fake


def levels(report):
    return {name: level for level, name, *_ in report.lines}


def test_healthy_setup(home, screenpipe):
    r = doctor.run()
    assert not r.failed, r.render()
    assert levels(r)["screenpipe"] == "ok"
    assert levels(r)["Teacher config"] == "ok"


def test_missing_config_points_to_setup_wizard(home, screenpipe):
    (home / "config.json").unlink()
    r = doctor.run()
    assert r.failed and levels(r)["Teacher config"] == "FAIL"
    assert "localhost:4000/setup" in r.render()


def test_invalid_config(home, screenpipe):
    (home / "config.json").write_text(json.dumps(example("config") | {"auto_share": "yes"}))
    assert levels(doctor.run())["Teacher config"] == "FAIL"


def test_missing_syllabus(home, screenpipe):
    (home / "cache" / "syllabus.json").unlink()
    assert levels(doctor.run())["Syllabus"] == "FAIL"


def test_empty_timetable_is_a_warning(home, screenpipe):
    (home / "config.json").write_text(json.dumps(example("config") | {"timetable": []}))
    r = doctor.run()
    assert levels(r)["Timetable"] == "warn" and not r.failed


def test_screenpipe_not_running(home, monkeypatch):
    monkeypatch.setenv("SCREENPIPE_URL", "http://127.0.0.1:9")
    r = doctor.run()
    assert levels(r)["screenpipe"] == "FAIL"
    assert "start the screenpipe app" in r.render()


def test_skip_screenpipe(home, monkeypatch):
    monkeypatch.setenv("SCREENPIPE_URL", "http://127.0.0.1:9")
    r = doctor.run(skip_screenpipe=True)
    assert "screenpipe" not in levels(r) and not r.failed


def test_output_is_ascii_for_windows_consoles(home, screenpipe):
    doctor.run().render().encode("ascii")


def test_cli_exit_codes(home, monkeypatch):
    script = [sys.executable, str(PIPE / "scripts" / "doctor.py"), "--skip-screenpipe"]
    assert subprocess.run(script, capture_output=True).returncode == 0
    (home / "config.json").unlink()
    r = subprocess.run(script, capture_output=True, text=True)
    assert r.returncode == 1 and "[FAIL]" in r.stdout
