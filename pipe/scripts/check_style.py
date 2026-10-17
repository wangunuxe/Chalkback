#!/usr/bin/env python3
"""Semantic checks for the new style profile (pipe step 6, TB5, owner B). Every rule must have real evidence.

    python check_style.py --profile ~/.chalkback/state/style_profile.json --inputs $WORK/style_inputs.json

Checks (errors → exit code 1):
- first passes the style_profile schema; teacher_id matches the config; version = next_version; updated_at = now
- at least one rule; rule texts (ignoring case and whitespace) are not duplicated
- origin=screen_history: frame_ids non-empty, all from this run's screen_history or from evidence in the old style profile;
  timestamp must be the time of one of those frames
- origin=teacher_edit: edit_ids non-empty, all from this run's edits or from evidence in the old style profile
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
    """Screenshots (frame_id → time) and review record ids that may be cited: this run's inputs + evidence already in the old style profile."""
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
        errors.append(f"teacher_id should be {inputs['teacher_id']}")
    if profile["version"] != inputs["next_version"]:
        errors.append(f"version should be {inputs['next_version']}")
    if datetime.fromisoformat(profile["updated_at"]) != datetime.fromisoformat(inputs["now"]):
        errors.append(f"updated_at should be {inputs['now']}")
    if not profile["rules"]:
        errors.append("at least one rule is required")

    frames, edit_ids = known_evidence(inputs)
    seen = set()
    for i, rule in enumerate(profile["rules"], 1):
        where = f"rule {i} \"{rule['rule']}\""
        key = re.sub(r"\s+", " ", rule["rule"]).strip().casefold()
        if key in seen:
            errors.append(f"{where} is duplicated")
        seen.add(key)

        ev = rule["evidence"]
        if rule["origin"] == "screen_history":
            ids = ev.get("frame_ids", [])
            if not ids:
                errors.append(f"{where}: screen_history rule must cite frame_ids")
            unknown = [f for f in ids if f not in frames]
            if unknown:
                errors.append(f"{where}: frame_ids {unknown} not in the inputs")
            if "timestamp" not in ev:
                errors.append(f"{where}: screen_history rule must have a timestamp")
            elif ids and not unknown and not any(datetime.fromisoformat(ev["timestamp"]) in frames[f] for f in ids):
                errors.append(f"{where}: timestamp is not the time of a cited screenshot")
        else:
            ids = ev.get("edit_ids", [])
            if not ids:
                errors.append(f"{where}: teacher_edit rule must cite edit_ids")
            unknown = [e for e in ids if e not in edit_ids]
            if unknown:
                errors.append(f"{where}: edit_ids {unknown} not in the inputs")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, type=Path)
    ap.add_argument("--inputs", required=True, type=Path, help="output of style_inputs.py")
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
