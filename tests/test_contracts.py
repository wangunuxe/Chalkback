"""contracts/ 自检：示例全部通过、pipe/schemas 与 contracts 同步、坏数据会被拒绝。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMAS = sorted(CONTRACTS.glob("*.schema.json"))


def name(p: Path) -> str:
    return p.name.removesuffix(".schema.json")


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.parametrize("schema_path", SCHEMAS, ids=name)
def test_every_contract_has_valid_example(schema_path):
    Draft202012Validator.check_schema(load(schema_path))
    Draft202012Validator(load(schema_path)).validate(load(CONTRACTS / "examples" / f"{name(schema_path)}.json"))


@pytest.mark.parametrize("schema_path", SCHEMAS, ids=name)
def test_pipe_schemas_in_sync(schema_path):
    assert (ROOT / "pipe" / "schemas" / schema_path.name).read_bytes() == schema_path.read_bytes(), "运行 make sync-schemas"


def test_coverage_share_rejects_private_fields():
    v = Draft202012Validator(load(CONTRACTS / "coverage_share.schema.json"))
    share = load(CONTRACTS / "examples" / "coverage_share.json")
    share["points"][0]["segment_ids"] = ["S-L-T1-20261017-1000-003"]
    assert not v.is_valid(share)


def test_timestamps_require_offset():
    v = Draft202012Validator(load(CONTRACTS / "attempt.schema.json"))
    attempt = load(CONTRACTS / "examples" / "attempt.json")
    attempt["at"] = "2026-10-17T11:30:12"
    assert not v.is_valid(attempt)


def test_quiz_answer_type_matches_question_type():
    v = Draft202012Validator(load(CONTRACTS / "quiz.schema.json"))
    quiz = load(CONTRACTS / "examples" / "quiz.json")
    quiz["questions"][2]["answer"] = "false"  # true_false 必须是布尔值
    assert not v.is_valid(quiz)


def test_validate_cli_examples():
    r = subprocess.run([sys.executable, str(ROOT / "pipe" / "scripts" / "validate.py"), "--examples"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
