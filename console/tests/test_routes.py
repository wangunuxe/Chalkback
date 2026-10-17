"""老师页面只允许本机；/play 对校园网开放（§6.3）。"""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app(tmp_path, monkeypatch):
    import subprocess, sys
    from .conftest import ROOT
    subprocess.run([sys.executable, str(ROOT / "tools" / "seed_mock_home.py"), "--home", str(tmp_path)], check=True)
    monkeypatch.setenv("CHALKBACK_HOME", str(tmp_path))
    from app import paths, outbox, main
    for m in (paths, outbox):
        importlib.reload(m)
    return main.app


def local(app):
    return TestClient(app, client=("127.0.0.1", 50000))


def lan(app):
    return TestClient(app, client=("192.168.1.23", 50000))


def test_review_lists_ready_lessons(app):
    assert local(app).get("/review").json() == {"lessons": ["L-T1-20261017-1000"]}


def test_teacher_pages_blocked_from_lan(app):
    for path in ("/review", "/setup", "/shares", "/style", "/review/L-T1-20261017-1000"):
        assert lan(app).get(path).status_code == 403, path


def test_play_open_to_lan(app):
    r = lan(app).get("/play/Q-L-T1-20261017-1000")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
