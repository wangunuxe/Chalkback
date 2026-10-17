#!/usr/bin/env python3
"""新风格文件的语义检查（pipe 第 6 步，TB5，负责人 B）。每条规则都必须有真实证据。

    python check_style.py --profile ~/.chalkback/state/style_profile.json --inputs $WORK/style_inputs.json

检查（错误 → 退出码 1）：
- 先通过 style_profile schema；teacher_id 与配置一致；version = next_version；updated_at = now
- 至少一条规则；规则文字（忽略大小写和空白）不重复
- origin=screen_history：frame_ids 非空，且都来自本次 screen_history 或旧风格文件里的证据；
  timestamp 必须是其中某一帧的时间
- origin=teacher_edit：edit_ids 非空，且都来自本次 edits 或旧风格文件里的证据
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate_file  # noqa: E402


def known_evidence(inputs: dict) -> tuple[dict[int, set[datetime]], set[str]]:
    """可以引用的截图（frame_id → 时间）和审核记录 id：本次输入 + 旧风格文件里已有的证据。"""
    frames: dict[int, set[datetime]] = {}
    edit_ids = {e["edit_id"] for e in inputs.get("edits", [])}
    for f in inputs.get("screen_history", []):
        frames.setdefault(f["frame_id"], set()).add(datetime.fromisoformat(f["timestamp"]))
    for rule in (inputs.get("current_profile") or {}).get("rules", []):
        ev = rule["evidence"]
        for fid in ev.get("frame_ids", []):
            if "timestamp" in ev:
                frames.setdefault(fid, set()).add(datetime.fromisoformat(ev["timestamp"]))
        edit_ids |= set(ev.get("edit_ids", []))
    return frames, edit_ids


def check(profile: dict, inputs: dict) -> list[str]:
    errors = []
    if inputs.get("teacher_id") and profile["teacher_id"] != inputs["teacher_id"]:
        errors.append(f"teacher_id 应为 {inputs['teacher_id']}")
    if profile["version"] != inputs["next_version"]:
        errors.append(f"version 应为 {inputs['next_version']}")
    if datetime.fromisoformat(profile["updated_at"]) != datetime.fromisoformat(inputs["now"]):
        errors.append(f"updated_at 应为 {inputs['now']}")
    if not profile["rules"]:
        errors.append("至少要有一条规则")

    frames, edit_ids = known_evidence(inputs)
    seen = set()
    for i, rule in enumerate(profile["rules"], 1):
        where = f"规则 {i}「{rule['rule']}」"
        key = re.sub(r"\s+", " ", rule["rule"]).strip().casefold()
        if key in seen:
            errors.append(f"{where} 重复")
        seen.add(key)

        ev = rule["evidence"]
        if rule["origin"] == "screen_history":
            ids = ev.get("frame_ids", [])
            if not ids:
                errors.append(f"{where}: screen_history 规则必须引用 frame_ids")
            unknown = [f for f in ids if f not in frames]
            if unknown:
                errors.append(f"{where}: frame_ids {unknown} 不在材料里")
            if "timestamp" not in ev:
                errors.append(f"{where}: screen_history 规则必须有 timestamp")
            elif ids and not unknown and not any(datetime.fromisoformat(ev["timestamp"]) in frames[f] for f in ids):
                errors.append(f"{where}: timestamp 不是所引截图的时间")
        else:
            ids = ev.get("edit_ids", [])
            if not ids:
                errors.append(f"{where}: teacher_edit 规则必须引用 edit_ids")
            unknown = [e for e in ids if e not in edit_ids]
            if unknown:
                errors.append(f"{where}: edit_ids {unknown} 不在材料里")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, type=Path)
    ap.add_argument("--inputs", required=True, type=Path, help="style_inputs.py 的输出")
    args = ap.parse_args(argv)

    schema_errors = validate_file("style_profile", args.profile)
    if schema_errors:
        print("\n".join(schema_errors), file=sys.stderr)
        return 1
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    errors = check(load(args.profile), load(args.inputs))
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print(f"ok  {args.profile}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
