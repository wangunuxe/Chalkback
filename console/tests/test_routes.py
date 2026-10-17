"""所有页面只允许本机访问，包括学生游戏 /play（§6.3：不做手机端）。"""
from fastapi.testclient import TestClient

from .conftest import LESSON, QUIZ


def lan(app):
    return TestClient(app, client=("192.168.1.23", 50000))


def test_review_lists_ready_lessons(client):
    assert client.get("/review").json() == {"lessons": [LESSON]}


def test_root_opens_console(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/console"


def test_every_page_blocked_from_lan(app, client):
    client.post(f"/review/{LESSON}/publish")
    for path in ("/console", "/review", "/setup", "/shares", "/style", f"/review/{LESSON}", f"/play/{QUIZ}"):
        assert lan(app).get(path).status_code == 403, path
    r = lan(app).post(f"/play/{QUIZ}/attempt", json={"nickname": "x", "q_id": "Q1", "response": 1})
    assert r.status_code == 403


def test_trusted_nets_only_extend_teacher_access(monkeypatch):
    import ipaddress
    from app import main
    monkeypatch.setattr(main, "TRUSTED_NETS", [ipaddress.ip_network("172.28.0.0/16")])
    assert main.is_local("172.28.0.1")
    assert not main.is_local("192.168.1.23")
    assert not main.is_local("not-an-ip")


def test_no_trusted_nets_by_default():
    from app import main
    assert not main.is_local("172.28.0.1")


def test_console_page_shows_real_lesson_without_external_resources(client):
    html = client.get("/console").text
    assert LESSON in html
    assert "Les pommes que j&#39;ai ___ étaient délicieuses." in html
    assert "Le passé composé" in html  # 知识点标题来自 cache/syllabus.json
    assert "{&#39;kp_id&#39;" not in html  # 提醒不再显示成 Python dict
    for external in ("https://", "http://", "cdn.", "fonts.googleapis"):
        assert external not in html, external


def test_console_page_without_lessons(client, home):
    import shutil
    shutil.rmtree(home / "outbox")
    r = client.get("/console")
    assert r.status_code == 200 and "No lesson ready yet" in r.text
