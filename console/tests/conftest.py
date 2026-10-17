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
