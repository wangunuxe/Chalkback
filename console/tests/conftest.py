import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts" / "examples"


def load_example(name: str):
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def schema():
    from jsonschema import Draft202012Validator

    def _get(name: str) -> Draft202012Validator:
        return Draft202012Validator(json.loads((ROOT / "contracts" / f"{name}.schema.json").read_text(encoding="utf-8")))

    return _get


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A fake ~/.chalkback/ generated from contracts/examples."""
    import subprocess
    import sys

    subprocess.run([sys.executable, str(ROOT / "tools" / "seed_mock_home.py"), "--home", str(tmp_path)], check=True,
                   capture_output=True)
    monkeypatch.setenv("CHALKBACK_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def app(home):
    import importlib

    from app import main, outbox, paths
    for m in (paths, outbox):
        importlib.reload(m)
    return main.app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app, client=("127.0.0.1", 50000))


LESSON = "L-T1-20261017-1000"
QUIZ = "Q-L-T1-20261017-1000"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
