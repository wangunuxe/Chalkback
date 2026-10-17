"""TD1: before the real implementation, each endpoint returns the sample data from contracts/examples."""
from __future__ import annotations

import json
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts" / "examples"


def example(name: str):
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
