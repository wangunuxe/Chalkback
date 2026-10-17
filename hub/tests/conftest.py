"""Temporary database for tests; does not touch hub/chalkback.db. HUB_DB must be set before importing app.
Tests use mock tokens, so test mode is turned on (HUB_MOCK_AUTH=1); production mode behaviour is tested separately in test_join.py."""
import os
import tempfile
from pathlib import Path

os.environ["HUB_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["HUB_MOCK_AUTH"] = "1"
