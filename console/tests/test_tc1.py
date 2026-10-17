from fastapi.testclient import TestClient
from app.main import app
from app import outbox
import os


def test_tc1_outbox_mock_creation():
    outbox.init_outbox_mock()
    assert os.path.exists("console/outbox/lesson_outbox.json")
    data = outbox.get_latest_outbox()
    assert data["lesson_id"] == "L2023_CH01"
    assert "coverages" in data
    assert "generated_questions" in data


def test_tc1_api_and_console_route():
    client = TestClient(app, client=("127.0.0.1", 50000))
    # Test API
    r = client.get("/api/console/outbox")
    assert r.status_code == 200
    json_data = r.json()
    assert json_data["lesson_id"] == "L2023_CH01"

    # Test Console Page
    r2 = client.get("/console")
    assert r2.status_code == 200
    assert "text/html" in r2.headers["content-type"]
    assert "Teacher Console" in r2.text
