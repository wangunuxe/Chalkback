"""Keep pipe.md consistent with the scripts.

Found during a trial run: step 0 (doctor.py, added in TB6) connects to screenpipe but was not in the mock rule,
so during local development the pipe stopped at step 0.
"""
import re
import subprocess
import sys

from conftest import PIPE

PIPE_MD = (PIPE / "pipe.md").read_text(encoding="utf-8")
SCRIPTS = PIPE / "scripts"


def mock_rule() -> str:
    """The CHALKBACK_MOCK=1 rule (may span several lines)."""
    m = re.search(r"CHALKBACK_MOCK=1.*?(?=\n- |\n\n)", PIPE_MD, re.S)
    assert m, "pipe.md has no CHALKBACK_MOCK=1 rule"
    return m.group(0)


def talks_to_screenpipe(path) -> bool:
    src = path.read_text(encoding="utf-8")
    return "SCREENPIPE_URL" in src or "extract_segments.search" in src


def test_every_screenpipe_script_is_covered_by_mock_rule():
    rule = mock_rule()
    scripts = sorted(p.name for p in SCRIPTS.glob("*.py") if talks_to_screenpipe(p))
    assert "doctor.py" in scripts and "lookback.py" in scripts
    missing = [s for s in scripts if s not in rule]
    assert not missing, f"these scripts connect to screenpipe but the mock rule in pipe.md does not mention them: {missing}"


def test_each_script_supports_its_mock_flag():
    """The rule reads "add `--x` to `a.py`, `b.py`; add `--y` to `c.py` (...)": check clause by clause
    that each script supports the flag assigned to it. A clause ends at ";", "(" or the end of the rule."""
    clauses = re.findall(r"add\s+`(--[\w-]+)`\s+to\s+(.*?)(?=;|\(|$)", mock_rule(), re.S)
    assert clauses
    for flag, scripts in clauses:
        named = re.findall(r"`(\w+\.py)`", scripts)
        assert named, f"the clause for {flag} names no script: {scripts!r}"
        for script in named:
            help_text = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"],
                                       capture_output=True, text=True).stdout
            assert flag in help_text, f"{script} does not support {flag}"


def test_every_script_referenced_in_pipe_md_exists():
    for script in set(re.findall(r"scripts/(\w+\.py)", PIPE_MD)):
        assert (SCRIPTS / script).exists(), f"pipe.md references a script that does not exist: {script}"


def test_every_flag_used_in_pipe_md_exists():
    """Every flag in the pipe.md commands must be known to its script. When A or B changes a script or pipe.md
    on their own, this catches interface mismatches."""
    for script, args in re.findall(r"scripts/(\w+\.py)([^\n`]*)", PIPE_MD):
        flags = set(re.findall(r"(?<![\w-])(--[a-z][\w-]*)", args))
        if not flags:
            continue
        help_text = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"],
                                   capture_output=True, text=True).stdout
        unknown = sorted(f for f in flags if f not in help_text)
        assert not unknown, f"pipe.md passes {script} flags it does not recognise: {unknown}"
