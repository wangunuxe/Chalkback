#!/usr/bin/env python3
"""ChalkBack environment check (TB6, owner B). Run it after installing; pipe.md also runs it first.

    python doctor.py [--skip-screenpipe]

Prints one line per check — [ok], [warn] or [FAIL] — with a fix for anything that is not ok.
Exit code 0 when there is no FAIL, 1 otherwise. Output is plain ASCII so it prints on any Windows console.
Only the standard library is used: this has to work on a fresh teacher laptop.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIPE_DIR = HERE.parent
MIN_PYTHON = (3, 11)
sys.path.insert(0, str(HERE))


class Report:
    def __init__(self):
        self.lines: list[tuple[str, str, str, str]] = []

    def add(self, level: str, name: str, detail: str = "", fix: str = "") -> None:
        self.lines.append((level, name, detail, fix))

    @property
    def failed(self) -> bool:
        return any(level == "FAIL" for level, *_ in self.lines)

    def render(self) -> str:
        out = []
        for level, name, detail, fix in self.lines:
            out.append(f"[{level}]".ljust(7) + f" {name}" + (f" - {detail}" if detail else ""))
            if fix and level != "ok":
                out.append(f"        fix: {fix}")
        out.append("")
        out.append("Some checks FAILED - fix them and run doctor.py again." if self.failed else "All required checks passed.")
        return "\n".join(out)


def chalkback_home() -> Path:
    return Path(os.environ.get("CHALKBACK_HOME", Path.home() / ".chalkback")).expanduser()


def check_python(r: Report) -> None:
    v = sys.version_info
    if v[:2] >= MIN_PYTHON:
        r.add("ok", "Python", f"{v.major}.{v.minor}.{v.micro}")
    else:
        r.add("FAIL", "Python", f"{v.major}.{v.minor} is too old (need 3.11+)",
              "install Python 3.12 from python.org (Windows: tick 'Add python.exe to PATH')")


def check_timezone(r: Report) -> None:
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("Europe/Paris")
        r.add("ok", "Time zone", "Europe/Paris")
    except Exception:
        r.add("warn", "Time zone", "Europe/Paris data not found, the laptop's local time zone will be used",
              "fine if this laptop is set to Paris time; otherwise run: python -m pip install tzdata")


def check_pipe_files(r: Report) -> None:
    needed = ["pipe.md", "prompts/gen_quiz.md", "prompts/alerts.md", "prompts/learn_style.md", "templates/game.html"]
    missing = [p for p in needed if not (PIPE_DIR / p).exists()]
    if missing:
        r.add("FAIL", "Pipe files", f"missing {', '.join(missing)}", "reinstall the pipe (see docs/SETUP.md, step 3)")
    else:
        r.add("ok", "Pipe files", str(PIPE_DIR))


def check_validator(r: Report) -> None:
    try:
        import validate
        d = validate.schema_dir()
    except SystemExit as e:
        r.add("FAIL", "Contract schemas", str(e), "reinstall the pipe (see docs/SETUP.md, step 3)")
        return
    engine = "jsonschema" if validate.validator_class().__name__ != "MiniValidator" else "built-in validator"
    r.add("ok", "Contract schemas", f"{len(list(d.glob('*.schema.json')))} schemas, {engine}")


def check_home(r: Report, home: Path) -> dict | None:
    config_path = home / "config.json"
    if not config_path.exists():
        r.add("FAIL", "Teacher config", f"{config_path} not found",
              "open http://localhost:4000/setup and finish the setup wizard")
        return None
    import validate
    errors = validate.validate_file("config", config_path)
    if errors:
        r.add("FAIL", "Teacher config", errors[0], "run the setup wizard again: http://localhost:4000/setup")
        return None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    r.add("ok", "Teacher config", f"teacher {config['teacher_id']}, {len(config['timetable'])} timetable slot(s)")
    if not config["timetable"]:
        r.add("warn", "Timetable", "empty - the pipe will never find a lesson to process",
              "add your lessons in the setup wizard: http://localhost:4000/setup")

    syllabus = home / "cache" / "syllabus.json"
    if not syllabus.exists():
        r.add("FAIL", "Syllabus", f"{syllabus} not found", "open the console once so it downloads the syllabus from the school Hub")
    else:
        errors = validate.validate_file("syllabus", syllabus)
        if errors:
            r.add("FAIL", "Syllabus", errors[0], "open the console once so it downloads the syllabus again")
        else:
            kps = len(json.loads(syllabus.read_text(encoding="utf-8"))["knowledge_points"])
            r.add("ok", "Syllabus", f"{kps} knowledge points")
    return config


def check_writable(r: Report, home: Path) -> None:
    bad = []
    for sub in ("outbox", "state", "work"):
        d = home / sub
        try:
            d.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=d):
                pass
        except OSError as e:
            bad.append(f"{sub}: {e.strerror or e}")
    if bad:
        r.add("FAIL", "Data folder", "; ".join(bad), f"make sure your user can write to {home}")
    else:
        r.add("ok", "Data folder", f"{home} is writable")


def check_screenpipe(r: Report) -> None:
    url = os.environ.get("SCREENPIPE_URL", "http://localhost:3030")
    key = os.environ.get("SCREENPIPE_LOCAL_API_KEY", "")
    req = urllib.request.Request(f"{url}/health", headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req, timeout=5):
            r.add("ok", "screenpipe", f"running at {url}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            r.add("ok", "screenpipe", f"running at {url} (API needs the key screenpipe gives to pipes)")
        else:
            r.add("warn", "screenpipe", f"{url}/health answered HTTP {e.code}", "restart the screenpipe app")
    except (urllib.error.URLError, OSError) as e:
        r.add("FAIL", "screenpipe", f"not reachable at {url} ({getattr(e, 'reason', e)})",
              "start the screenpipe app and keep it running during lessons")


def run(skip_screenpipe: bool = False) -> Report:
    r = Report()
    check_python(r)
    check_timezone(r)
    check_pipe_files(r)
    check_validator(r)
    home = chalkback_home()
    check_home(r, home)
    check_writable(r, home)
    if not skip_screenpipe:
        check_screenpipe(r)
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-screenpipe", action="store_true", help="do not check that screenpipe is running")
    args = ap.parse_args(argv)
    report = run(args.skip_screenpipe)
    print(report.render())
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
