"""Recording panel (/screenpipe/*): talks to a fake screenpipe, never to the Hub."""
import httpx
import pytest
from fastapi.testclient import TestClient


class FakeScreenpipe:
    """Answers like the screenpipe local API; `open=False` behaves like the app being quit (history only)."""

    def __init__(self, open=True):
        self.open = open
        self.mic_running = False
        self.screen_running = False
        self.requests = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path, request))
        path = request.url.path
        if path == "/health":
            return httpx.Response(503, json={"status": "degraded"})
        if path == "/search":
            if request.url.params["content_type"] == "audio":
                return httpx.Response(200, json={"data": [
                    {"type": "Audio", "content": {"transcription": "Le passé composé avec avoir", "device_type": "Input",
                                                  "timestamp": "2026-10-18T09:01:00Z"}},
                    {"type": "Audio", "content": {"transcription": "music from the speakers", "device_type": "Output",
                                                  "timestamp": "2026-10-18T09:02:00Z"}},
                ]})
            return httpx.Response(200, json={"data": [
                {"type": "OCR", "content": {"text": "J'ai mangé une pomme", "app_name": "PowerPoint",
                                            "timestamp": "2026-10-18T09:03:00Z"}},
            ]})
        if path == "/audio/device/status":  # like real screenpipe, still answers after the app was quit
            return httpx.Response(200, json=[
                {"name": "Microphone (input)", "is_running": self.mic_running and self.open},
                {"name": "Speakers (output)", "is_running": self.mic_running and self.open},
            ])
        if not self.open:
            return httpx.Response(409, json={"error": "search_only", "message": "Screenpipe was quit"})
        if path == "/audio/list":
            return httpx.Response(200, json=[{"name": "Microphone (input)", "is_default": True}])
        if path == "/vision/device/status":
            return httpx.Response(200, json=[{"monitor_id": 1, "is_running": self.screen_running}])
        if path == "/vision/list":
            return httpx.Response(200, json=[{"id": 1, "name": "Display 1"}])
        if path in ("/audio/start", "/audio/stop"):
            self.mic_running = path == "/audio/start"
            return httpx.Response(200, json={"success": True})
        if path in ("/vision/device/start", "/vision/device/stop"):
            self.screen_running = path == "/vision/device/start"
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404)

    def called(self, method, path):
        return any(m == method and p == path for m, p, _ in self.requests)


@pytest.fixture
def fake(monkeypatch):
    from app import screenpipe

    fake = FakeScreenpipe()
    monkeypatch.setenv("SCREENPIPE_LOCAL_API_KEY", "sp-test-key")

    def client():
        return httpx.Client(base_url="http://localhost:3030", transport=httpx.MockTransport(fake.handler),
                            headers={"Authorization": f"Bearer {screenpipe.os.environ['SCREENPIPE_LOCAL_API_KEY']}"})

    monkeypatch.setattr(screenpipe, "_client", client)
    return fake


@pytest.fixture(autouse=True)
def no_hub(monkeypatch):
    """Nothing in the Recording panel may reach the Hub."""
    from app import hub_client

    def refuse(*args, **kwargs):
        raise AssertionError("the Recording panel must never talk to the Hub")

    monkeypatch.setattr(hub_client.HubClient, "__init__", refuse)


def test_status_lists_microphones_only(client, fake):
    s = client.get("/screenpipe/status").json()
    assert s["app_open"] is True and s["recording"] is False
    assert s["microphones"] == [{"name": "Microphone", "running": False}]


def test_start_and_stop_recording(client, fake):
    s = client.post("/screenpipe/recording/start").json()
    assert s["recording"] is True and s["screens"] == 1
    assert fake.called("POST", "/audio/start") and fake.called("POST", "/vision/device/start")
    start = next(r for m, p, r in fake.requests if p == "/vision/device/start")
    assert start.read() == b'{"monitor_id":1}'

    s = client.post("/screenpipe/recording/stop").json()
    assert s["recording"] is False
    assert fake.called("POST", "/audio/stop") and fake.called("POST", "/vision/device/stop")


def test_closed_app_is_reported_not_an_error(client, fake):
    fake.open = False
    s = client.get("/screenpipe/status").json()
    assert s == {"app_open": False, "recording": False, "health": "degraded", "microphones": [], "screens": 0}
    r = client.post("/screenpipe/recording/start")
    assert r.status_code == 409 and "open the screenpipe app" in r.json()["detail"]


def test_unreachable_screenpipe(client, monkeypatch):
    from app import screenpipe

    def down(request):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(screenpipe, "_client", lambda: httpx.Client(transport=httpx.MockTransport(down), base_url="http://x"))
    r = client.get("/screenpipe/status")
    assert r.status_code == 502 and "unreachable" in r.json()["detail"]


def test_wrong_api_key(client, monkeypatch):
    from app import screenpipe

    monkeypatch.setattr(screenpipe, "_client", lambda: httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"error": "unauthorized"})), base_url="http://x"))
    r = client.get("/screenpipe/recent")
    assert r.status_code == 502 and "SCREENPIPE_LOCAL_API_KEY" in r.json()["detail"]


def test_recent_is_teacher_voice_and_screen_newest_first(client, fake):
    body = client.get("/screenpipe/recent?minutes=5").json()
    assert body["minutes"] == 5
    assert [(i["kind"], i["text"]) for i in body["items"]] == [
        ("screen", "J'ai mangé une pomme"),
        ("speech", "Le passé composé avec avoir"),
    ]
    search = next(r for m, p, r in fake.requests if p == "/search")
    assert "start_time" in search.url.params
    assert search.headers["Authorization"] == "Bearer sp-test-key"


def test_recent_minutes_are_bounded(client, fake):
    assert client.get("/screenpipe/recent?minutes=0").status_code == 422
    assert client.get("/screenpipe/recent?minutes=500").status_code == 422


def test_process_runs_the_pipe_in_background(client, monkeypatch):
    from app import screenpipe

    started = []
    monkeypatch.setattr(screenpipe.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(screenpipe.subprocess, "Popen", lambda cmd, **kw: started.append(cmd))
    body = client.post("/screenpipe/process").json()
    assert body["status"] == "started"
    assert started == [["/usr/bin/npx", "-y", "screenpipe@latest", "pipe", "run", "pipe"]]


def test_process_without_node(client, monkeypatch):
    from app import screenpipe

    monkeypatch.setattr(screenpipe.shutil, "which", lambda name: None)
    r = client.post("/screenpipe/process")
    assert r.status_code == 503 and "npx not found" in r.json()["detail"]


def test_panel_blocked_from_lan(app, fake):
    lan = TestClient(app, client=("192.168.1.20", 50000))
    for method, path in (("GET", "/screenpipe/status"), ("GET", "/screenpipe/recent"), ("POST", "/screenpipe/recording/start")):
        assert lan.request(method, path).status_code == 403
    assert fake.requests == []


def test_console_page_has_recording_panel(client, fake):
    html = client.get("/console").text
    assert 'id="recorder"' in html and "/screenpipe/recording/start" in html
    assert "nothing is sent to the school Hub" in html
