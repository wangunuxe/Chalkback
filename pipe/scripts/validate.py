#!/usr/bin/env python3
"""按 contracts/ 校验契约文件（TB1，负责人 B）。

用法：
    python validate.py <contract> <file>     # 例：validate.py coverage outbox/L-.../coverage.json
    python validate.py --examples            # 校验 contracts/examples/ 全部示例

文件可以是单个 JSON 对象、JSON 数组（如 segments.json）或 .jsonl（如 edits.jsonl），
数组和 .jsonl 逐条校验。全部通过时退出码 0，否则打印每条错误并退出码 1。

schema 查找顺序：$CHALKBACK_SCHEMAS → pipe/schemas/（随 pipe 安装）→ 仓库 contracts/。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("validate.py 需要 jsonschema：pip install jsonschema")

HERE = Path(__file__).resolve().parent
SCHEMA_DIRS = [
    Path(p) for p in [os.environ.get("CHALKBACK_SCHEMAS", "")] if p
] + [HERE.parent / "schemas", HERE.parent.parent / "contracts"]


def schema_dir() -> Path:
    for d in SCHEMA_DIRS:
        if d.is_dir() and any(d.glob("*.schema.json")):
            return d
    sys.exit(f"找不到 schema 目录，已尝试：{', '.join(map(str, SCHEMA_DIRS))}")


def load_validator(contract: str) -> Draft202012Validator:
    path = schema_dir() / f"{contract}.schema.json"
    if not path.exists():
        known = sorted(p.name.removesuffix(".schema.json") for p in schema_dir().glob("*.schema.json"))
        sys.exit(f"未知契约 {contract!r}，可选：{', '.join(known)}")
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


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
    ap.add_argument("--examples", action="store_true", help="校验仓库 contracts/examples/ 全部示例")
    args = ap.parse_args(argv)

    if args.examples:
        examples = HERE.parent.parent / "contracts" / "examples"
        targets = [(p.stem, p) for p in sorted(examples.glob("*.json"))]
        if not targets:
            ap.error(f"{examples} 里没有示例")
    elif args.contract and args.file:
        targets = [(args.contract, args.file)]
    else:
        ap.error("需要 <contract> <file> 或 --examples")

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
