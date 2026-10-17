"""Temporary database for tests; does not touch hub/chalkback.db. HUB_DB must be set before importing app.
Tests use mock tokens, so test mode is turned on (HUB_MOCK_AUTH=1); production mode behaviour is tested separately in test_join.py.
The Hub starts with no syllabus (see test_empty_hub.py), so the example syllabus is approved here as v1, as `make mock` would."""
import json
import os
import tempfile
from contextlib import closing
from pathlib import Path

os.environ["HUB_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["HUB_MOCK_AUTH"] = "1"

from app import db  # noqa: E402
from app.mock import example  # noqa: E402


def approve_example_syllabus() -> None:
    syllabus = example("syllabus")
    with closing(db.connect()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO syllabi (workspace_id, syllabus_id, version, status, body, approved_at)"
            " VALUES (?, ?, ?, 'approved', ?, '2026-10-17T00:00:00+00:00')",
            (db.DEMO_WORKSPACE[0], syllabus["syllabus_id"], syllabus["version"], json.dumps(syllabus, ensure_ascii=False)),
        )


approve_example_syllabus()
