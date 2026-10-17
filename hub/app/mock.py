"""TD1：在真实实现之前，各接口返回 contracts/examples 里的示例数据。"""
from __future__ import annotations

import json
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts" / "examples"


def example(name: str):
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
