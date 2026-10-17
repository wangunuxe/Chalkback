"""Share (A3), withdraw (A5), setup (A1): when the Hub fails, report the error truthfully, do not pretend success, do not write a mock token."""
import json

import httpx
import pytest

from app import hub_client
from app.hub_client import HubClient

from .conftest import LESSON, load_example


def hub_down(*args, **kwargs):
    raise httpx.ConnectError("connection refused")


def shares(home):
    path = home / "state" / "shares.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def test_share_records_hub_share_id(client, home, monkeypatch):
    sent = []
    monkeypatch.setattr(HubClient, "share_coverage", lambda self, body: sent.append(body) or f"SH-{len(sent)}")
    assert client.post(f"/review/{LESSON}/share").json() == {"status": "shared", "share_id": "SH-1"}
    assert sent == [load_example("coverage_share")]
    # Re-uploading the same lesson: the Hub replaces the old one, and locally only the latest record is kept
    client.post(f"/review/{LESSON}/share")
    assert [s["share_id"] for s in shares(home)] == ["SH-2"]
    assert client.get(f"/review/{LESSON}").json()["share"]["share_id"] == "SH-2"


def test_share_fails_loudly_when_hub_is_down(client, home, monkeypatch):
    monkeypatch.setattr(HubClient, "share_coverage", hub_down)
    r = client.post(f"/review/{LESSON}/share")
    assert r.status_code == 502
    assert shares(home) == []


def test_share_needs_setup(client, home):
    (home / "config.json").unlink()
    assert client.post(f"/review/{LESSON}/share").status_code == 409


def test_withdraw(client, home, monkeypatch):
    monkeypatch.setattr(HubClient, "share_coverage", lambda self, body: "SH-1")
    client.post(f"/review/{LESSON}/share")

    monkeypatch.setattr(HubClient, "revoke", hub_down)
    assert client.delete("/shares/SH-1").status_code == 502
    assert len(shares(home)) == 1  # the Hub did not delete it, so the local record is kept

    revoked = []
    monkeypatch.setattr(HubClient, "revoke", lambda self, share_id: revoked.append(share_id))
    assert client.delete("/shares/SH-1").json() == {"status": "withdrawn", "share_id": "SH-1"}
    assert revoked == ["SH-1"] and shares(home) == []
    assert client.delete("/shares/SH-1").status_code == 404


@pytest.mark.parametrize("status,ok", [(204, True), (404, True), (403, False), (500, False)])
def test_revoke_treats_missing_share_as_done(status, ok):
    client = HubClient("https://hub.test", "token")
    client._http = httpx.Client(base_url="https://hub.test", transport=httpx.MockTransport(lambda req: httpx.Response(status)))
    if ok:
        client.revoke("SH-1")
    else:
        with pytest.raises(httpx.HTTPStatusError):
            client.revoke("SH-1")


SETUP = {"invite_code": "DEMO-TEACHER", "teacher_name": "Mme Martin", "hub_url": "https://hub.test",
         "timetable": [{"day": "TUE", "start": "09:00", "end": "10:00", "class_id": "4B"}]}


def test_setup_requires_explicit_consent(client):
    assert client.post("/setup", json=SETUP).status_code == 400
    assert client.post("/setup", json={**SETUP, "consent": False}).status_code == 400


def test_setup_fails_without_hub_and_writes_no_mock_token(client, home, monkeypatch):
    (home / "config.json").unlink()
    monkeypatch.setattr(HubClient, "join", hub_down)
    assert client.post("/setup", json={**SETUP, "consent": True}).status_code == 502
    assert not (home / "config.json").exists()


def test_setup_writes_config_from_join(client, home, monkeypatch, schema):
    edits_before = (home / "state" / "edits.jsonl").read_text(encoding="utf-8")
    syllabus = load_example("syllabus")
    monkeypatch.setattr(HubClient, "join", lambda self, **kw: {"teacher_id": "T7", "token": "tok-7", "workspace_id": "W9"})
    monkeypatch.setattr(HubClient, "current_syllabus", lambda self: syllabus)

    r = client.post("/setup", json={**SETUP, "consent": True})
    assert r.json() == {"status": "configured", "teacher_id": "T7", "workspace_id": "W9"}
    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    schema("config").validate(config)
    assert (config["token"], config["workspace_id"], config["syllabus_id"]) == ("tok-7", "W9", syllabus["syllabus_id"])
    assert json.loads((home / "cache" / "syllabus.json").read_text(encoding="utf-8")) == syllabus
    assert (home / "state" / "edits.jsonl").read_text(encoding="utf-8") == edits_before  # no non-contract records are written to edits.jsonl


def test_hub_error_messages():
    assert hub_client.hub_error(httpx.ConnectError("x")).status_code == 502
