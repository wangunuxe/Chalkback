import json
import sys
from pathlib import Path

import pytest

PIPE = Path(__file__).resolve().parents[1]
ROOT = PIPE.parent
EXAMPLES = ROOT / "contracts" / "examples"

sys.path.insert(0, str(PIPE / "scripts"))


def example(name: str):
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def write_json(tmp_path):
    def _write(name: str, data) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path
    return _write
