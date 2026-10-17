import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "console"))

from fastapi.testclient import TestClient
from app.main import app
from app import outbox
import os

def run_tests():
    print("Running TC1 verification...")
    outbox.init_outbox_mock()
    assert os.path.exists("console/outbox/lesson_outbox.json"), "lesson_outbox.json not created"
    data = outbox.get_latest_outbox()
    assert data["lesson_id"] == "L2023_CH01", f"Unexpected lesson_id: {data.get('lesson_id')}"
    assert "coverages" in data, "Missing coverages"
    assert "generated_questions" in data, "Missing generated_questions"
    print("Outbox mock creation test PASSED.")

    client = TestClient(app, client=("127.0.0.1", 50000))
    r = client.get("/api/console/outbox")
    assert r.status_code == 200, f"API failed with status {r.status_code}"
    json_data = r.json()
    assert json_data["lesson_id"] == "L2023_CH01"
    print("API /api/console/outbox test PASSED.")

    r2 = client.get("/console")
    assert r2.status_code == 200, f"Console page failed with status {r2.status_code}"
    assert "text/html" in r2.headers["content-type"]
    assert "Teacher Console" in r2.text
    print("Console page GET /console test PASSED.")
    print("All TC1 tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()
