#!/usr/bin/env python3
"""Validate contract files against contracts/ (TB1, owner B).

Usage:
    python validate.py <contract> <file>     # e.g. validate.py coverage outbox/L-.../coverage.json
    python validate.py --examples            # validate every example in contracts/examples/

A file can be a single JSON object, a JSON array (e.g. segments.json) or .jsonl (e.g. edits.jsonl);
arrays and .jsonl are validated record by record. Exit code 0 when everything passes, otherwise every error is printed and the exit code is 1.

Schema lookup order: $CHALKBACK_SCHEMAS → pipe/schemas/ (installed with pipe) → the repo's contracts/.

Validation engine: jsonschema if installed; otherwise (the usual case on a teacher's computer) the MiniValidator below,
which depends only on the standard library and supports the keywords contracts/ uses. If a schema uses a keyword it does not support, it fails loudly instead of silently passing.
CHALKBACK_VALIDATOR=builtin forces MiniValidator (used by tests checking both engines agree).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent

# keywords that are documentation only and take no part in validation
ANNOTATIONS = {"$schema", "$id", "title", "description", "$comment", "$defs", "examples", "default"}
SUPPORTED = ANNOTATIONS | {
    "type", "enum", "const", "properties", "required", "additionalProperties", "minProperties",
    "items", "minItems", "minLength", "pattern", "minimum", "maximum", "allOf", "if", "then", "$ref",
}
TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer()),
}


@dataclass
class SchemaError:
    message: str
    absolute_path: list = field(default_factory=list)


def json_equal(a, b) -> bool:
    """Equality with JSON semantics: true is not equal to 1."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(json_equal(x, y) for x, y in zip(a, b))
    return a == b


class MiniValidator:
    """A subset of JSON Schema 2020-12, enough for contracts/. Same interface as jsonschema's iter_errors."""

    def __init__(self, schema: dict):
        self.root = schema
        self._check_keywords(schema, "#")

    def _check_keywords(self, node, where: str) -> None:
        if not isinstance(node, dict):
            return
        unknown = set(node) - SUPPORTED
        if unknown:
            raise ValueError(f"schema uses keywords {sorted(unknown)} at {where} that the built-in validator does not support; please install jsonschema")
        for key in ("properties", "$defs"):
            for name, sub in node.get(key, {}).items():
                self._check_keywords(sub, f"{where}/{key}/{name}")
        for key in ("items", "additionalProperties", "if", "then"):
            if isinstance(node.get(key), dict):
                self._check_keywords(node[key], f"{where}/{key}")
        for i, sub in enumerate(node.get("allOf", [])):
            self._check_keywords(sub, f"{where}/allOf/{i}")

    def is_valid(self, instance) -> bool:
        return next(self.iter_errors(instance), None) is None

    def validate(self, instance) -> None:
        err = next(self.iter_errors(instance), None)
        if err is not None:
            raise ValueError(err.message)

    def iter_errors(self, instance, schema=None, path=()):
        schema = self.root if schema is None else schema
        s = schema
        p = list(path)

        if "$ref" in s:
            yield from self.iter_errors(instance, self._resolve(s["$ref"]), path)
        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(TYPES[t](instance) for t in types):
                yield SchemaError(f"{instance!r} is not of type {', '.join(map(repr, types))}", p)
                return
        if "enum" in s and not any(json_equal(instance, e) for e in s["enum"]):
            yield SchemaError(f"{instance!r} is not one of {s['enum']!r}", p)
        if "const" in s and not json_equal(instance, s["const"]):
            yield SchemaError(f"{s['const']!r} was expected", p)

        if isinstance(instance, dict):
            for name in s.get("required", []):
                if name not in instance:
                    yield SchemaError(f"{name!r} is a required property", p)
            if "minProperties" in s and len(instance) < s["minProperties"]:
                yield SchemaError(f"{instance!r} does not have enough properties", p)
            props = s.get("properties", {})
            for name, value in instance.items():
                if name in props:
                    yield from self.iter_errors(value, props[name], (*path, name))
            extra = [k for k in instance if k not in props]
            if extra and "additionalProperties" in s:
                ap = s["additionalProperties"]
                if ap is False:
                    yield SchemaError(f"Additional properties are not allowed ({', '.join(map(repr, extra))} was unexpected)", p)
                elif isinstance(ap, dict):
                    for name in extra:
                        yield from self.iter_errors(instance[name], ap, (*path, name))

        if isinstance(instance, list):
            if "minItems" in s and len(instance) < s["minItems"]:
                yield SchemaError(f"{instance!r} should have at least {s['minItems']} items", p)
            if isinstance(s.get("items"), dict):
                for i, item in enumerate(instance):
                    yield from self.iter_errors(item, s["items"], (*path, i))

        if isinstance(instance, str):
            if "minLength" in s and len(instance) < s["minLength"]:
                yield SchemaError(f"{instance!r} should be non-empty" if s["minLength"] == 1 else f"{instance!r} is too short", p)
            if "pattern" in s and not re.search(s["pattern"], instance):
                yield SchemaError(f"{instance!r} does not match {s['pattern']!r}", p)

        if TYPES["number"](instance):
            if "minimum" in s and instance < s["minimum"]:
                yield SchemaError(f"{instance!r} is less than the minimum of {s['minimum']!r}", p)
            if "maximum" in s and instance > s["maximum"]:
                yield SchemaError(f"{instance!r} is greater than the maximum of {s['maximum']!r}", p)

        for sub in s.get("allOf", []):
            yield from self.iter_errors(instance, sub, path)
        if "if" in s and "then" in s:
            if next(self.iter_errors(instance, s["if"], path), None) is None:
                yield from self.iter_errors(instance, s["then"], path)

    def _resolve(self, ref: str):
        if not ref.startswith("#/"):
            raise ValueError(f"the built-in validator only supports $ref within the same file: {ref}")
        node = self.root
        for part in ref[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node


def validator_class():
    if os.environ.get("CHALKBACK_VALIDATOR") == "builtin":
        return MiniValidator
    try:
        from jsonschema import Draft202012Validator
        return Draft202012Validator
    except ImportError:
        return MiniValidator


SCHEMA_DIRS = [
    Path(p) for p in [os.environ.get("CHALKBACK_SCHEMAS", "")] if p
] + [HERE.parent / "schemas", HERE.parent.parent / "contracts"]


def schema_dir() -> Path:
    for d in SCHEMA_DIRS:
        if d.is_dir() and any(d.glob("*.schema.json")):
            return d
    sys.exit(f"schema directory not found, tried: {', '.join(map(str, SCHEMA_DIRS))}")


def load_validator(contract: str):
    path = schema_dir() / f"{contract}.schema.json"
    if not path.exists():
        known = sorted(p.name.removesuffix(".schema.json") for p in schema_dir().glob("*.schema.json"))
        sys.exit(f"unknown contract {contract!r}, choices: {', '.join(known)}")
    return validator_class()(json.loads(path.read_text(encoding="utf-8")))


def load_records(path: Path) -> list[tuple[str, object]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [(f"{path}:{i}", json.loads(line)) for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    data = json.loads(text)
    if isinstance(data, list):
        return [(f"{path}[{i}]", item) for i, item in enumerate(data)]
    return [(str(path), data)]


def validate_file(contract: str, path: Path) -> list[str]:
    validator = load_validator(contract)
    errors = []
    try:
        records = load_records(path)
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path}: {e}"]
    for where, record in records:
        for err in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path)):
            loc = "/".join(map(str, err.absolute_path)) or "<root>"
            errors.append(f"{where}: {loc}: {err.message}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("contract", nargs="?")
    ap.add_argument("file", nargs="?", type=Path)
    ap.add_argument("--examples", action="store_true", help="validate every example in the repo's contracts/examples/")
    args = ap.parse_args(argv)

    if args.examples:
        examples = HERE.parent.parent / "contracts" / "examples"
        targets = [(p.stem, p) for p in sorted(examples.glob("*.json"))]
        if not targets:
            ap.error(f"no examples in {examples}")
    elif args.contract and args.file:
        targets = [(args.contract, args.file)]
    else:
        ap.error("need <contract> <file> or --examples")

    failed = False
    for contract, path in targets:
        errors = validate_file(contract, path)
        if errors:
            failed = True
            print("\n".join(errors), file=sys.stderr)
        else:
            print(f"ok  {contract:15} {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
