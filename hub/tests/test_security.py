"""公网部署的安全默认值，以及上传内容检查（TD2、TD4）。

- 默认是正式模式：不接受 mock token，公开的 DEMO-* 邀请码不能用；学校的邀请码用 HUB_INVITES 设置。
- 老师只能上传自己的课；考纲版本必须已批准；知识点必须在那个版本里。
"""
import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.mock import example
from app.routes import join as join_route

client = TestClient(app)
T1 = {"Authorization": "Bearer mock-token-T1"}
HEAD = {"Authorization": "Bearer mock-token-H1"}


@pytest.fixture
def production(monkeypatch):
    monkeypatch.delenv("HUB_MOCK_AUTH", raising=False)
    monkeypatch.delenv("HUB_INVITES", raising=False)


def join(code, role="teacher", name="Mme Test"):
    return client.post("/api/join", json={"invite_code": code, "display_name": name, "role": role})


def test_mock_tokens_off_by_default(production):
    assert client.get("/api/syllabus/current", headers=T1).status_code == 401


def test_demo_invites_off_by_default(production):
    assert join("DEMO-ADMIN", "admin").status_code == 404
    assert join("DEMO-TEACHER").status_code == 404


def test_school_invites_from_env(production, monkeypatch):
    monkeypatch.setenv("HUB_INVITES", "teacher=ECOLE-T-7f3,head=ECOLE-H-91c,admin=ECOLE-A-2d8")
    r = join("ECOLE-T-7f3")
    assert r.status_code == 200 and r.json()["teacher_id"].startswith("T")
    assert join("ECOLE-T-7f3", "admin").status_code == 403
    assert join("DEMO-ADMIN", "admin").status_code == 404
    token = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/api/syllabus/current", headers=token).status_code == 200


def test_bad_invite_config_is_reported(monkeypatch):
    monkeypatch.setenv("HUB_INVITES", "teacher:OOPS")
    with pytest.raises(ValueError, match="HUB_INVITES"):
        db.invite_codes()


def test_home_page_does_not_publish_codes():
    html = client.get("/").text
    assert "DEMO-ADMIN" not in html and "DEMO-HEAD" not in html


def test_member_ids_do_not_collide(monkeypatch):
    first = join("DEMO-TEACHER").json()["teacher_id"]
    # 模拟另一个人同时加入：第一次算出的编号已被占用，要重算而不是返回 500
    calls = []
    real = join_route.next_member_id

    def racing(conn, role):
        calls.append(role)
        return first if len(calls) == 1 else real(conn, role)

    monkeypatch.setattr(join_route, "next_member_id", racing)
    r = join("DEMO-TEACHER")
    assert r.status_code == 200 and r.json()["teacher_id"] != first and len(calls) == 2


def share(**changes):
    return client.post("/api/coverage", json={**example("coverage_share"), **changes}, headers=T1)


def test_cannot_share_someone_elses_lesson():
    r = share(lesson_id="L-T2-20261017-1000")
    assert r.status_code == 422 and "belongs to T2" in str(r.json())


def test_syllabus_version_must_be_approved():
    r = share(syllabus_version=99)
    assert r.status_code == 422 and "not an approved version" in str(r.json())
    draft = {**example("syllabus"), "syllabus_id": "brouillon-4e"}
    version = client.post("/api/syllabus", json=draft, headers=HEAD).json()["version"]
    r = share(syllabus_id="brouillon-4e", syllabus_version=version)  # 草稿还没批准
    assert r.status_code == 422


def test_knowledge_points_must_exist():
    body = example("coverage_share")
    body["points"] = body["points"] + [{"kp_id": "KPZZ", "covered": True, "minutes": 2}]
    r = client.post("/api/coverage", json=body, headers=T1)
    assert r.status_code == 422 and "KPZZ" in str(r.json())


def test_valid_share_still_accepted():
    assert share().status_code == 200
