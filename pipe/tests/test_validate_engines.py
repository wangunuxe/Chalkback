"""The built-in MiniValidator must agree with jsonschema: it guards the contracts when the teacher's computer has no jsonschema.

Differential test: generate many variants of each contract example (drop fields, add fields, change types, change values); both engines must reach
the same "valid / invalid" verdict for every variant.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import validate
from conftest import EXAMPLES, PIPE, ROOT
from validate import MiniValidator

SCHEMAS = sorted((ROOT / "contracts").glob("*.schema.json"))
WRONG = [None, True, 0, -1, 1.5, "", "x", [], {}, [1], {"x": 1}]


def name(p: Path) -> str:
    return p.name.removesuffix(".schema.json")


def leaves(node, path=()):
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaves(v, (*path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from leaves(v, (*path, i))


def set_at(doc, path, value):
    doc = copy.deepcopy(doc)
    if not path:
        return value
    node = doc
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value
    return doc


def variants(example):
    yield example
    for path, node in leaves(example):
        for value in WRONG:
            yield set_at(example, path, value)
        if isinstance(node, dict):
            for key in node:
                yield set_at(example, path, {k: v for k, v in node.items() if k != key})
            yield set_at(example, path, {**node, "unexpected": 1})
        if isinstance(node, list):
            yield set_at(example, path, [])
        if isinstance(node, str):
            yield set_at(example, path, node + "Z")
            yield set_at(example, path, node[:-1])


@pytest.mark.parametrize("schema_path", SCHEMAS, ids=name)
def test_builtin_agrees_with_jsonschema(schema_path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    ref, mini = Draft202012Validator(schema), MiniValidator(schema)
    example = json.loads((EXAMPLES / f"{name(schema_path)}.json").read_text(encoding="utf-8"))
    checked = 0
    for doc in variants(example):
        assert mini.is_valid(doc) == ref.is_valid(doc), json.dumps(doc, ensure_ascii=False)[:300]
        checked += 1
    assert checked > 20


def test_quiz_answer_types_by_question_type():
    mini = MiniValidator(json.loads((ROOT / "contracts" / "quiz.schema.json").read_text(encoding="utf-8")))
    quiz = json.loads((EXAMPLES / "quiz.json").read_text(encoding="utf-8"))
    assert mini.is_valid(quiz)
    for i, bad in ((0, True), (1, 3), (2, "false")):   # mcq cannot be a boolean, fill_blank cannot be a number, true_false cannot be a string
        assert not mini.is_valid(set_at(quiz, ("questions", i, "answer"), bad))


def test_error_has_path_and_message():
    mini = MiniValidator(json.loads((ROOT / "contracts" / "attempt.schema.json").read_text(encoding="utf-8")))
    errors = list(mini.iter_errors({"quiz_id": "Q-L-T1-20261017-1000", "nickname": "a", "q_id": "Q1", "response": 1,
                                    "correct": "yes", "time_ms": 1, "at": "2026-10-17T11:30:12+02:00"}))
    assert [(e.absolute_path, "boolean" in e.message) for e in errors] == [(["correct"], True)]


def test_unsupported_keyword_fails_loudly():
    with pytest.raises(ValueError, match="oneOf"):
        MiniValidator({"type": "object", "properties": {"a": {"oneOf": [{"type": "string"}]}}})


def test_cli_works_without_jsonschema_installed(tmp_path):
    """Simulate the teacher's computer: jsonschema cannot be imported, yet validate.py still validates every example and rejects bad files."""
    blocker = tmp_path / "jsonschema.py"
    blocker.write_text("raise ImportError('not installed')")
    env = {"PYTHONPATH": str(tmp_path), "PATH": ""}
    script = str(PIPE / "scripts" / "validate.py")
    ok = subprocess.run([sys.executable, script, "--examples"], capture_output=True, text=True, env=env)
    assert ok.returncode == 0, ok.stderr

    bad = tmp_path / "attempts.jsonl"
    bad.write_text('{"quiz_id": "nope"}\n', encoding="utf-8")
    r = subprocess.run([sys.executable, script, "attempt", str(bad)], capture_output=True, text=True, env=env)
    assert r.returncode == 1 and "required" in r.stderr


def test_engine_selection(monkeypatch):
    monkeypatch.setenv("CHALKBACK_VALIDATOR", "builtin")
    assert validate.validator_class() is MiniValidator
    monkeypatch.delenv("CHALKBACK_VALIDATOR")
    assert validate.validator_class() is Draft202012Validator
