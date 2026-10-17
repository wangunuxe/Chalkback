"""pipe.md 与脚本保持一致。

试跑时发现：TB6 加的第 0 步 doctor.py 会连 screenpipe，但没写进 mock 说明，本地开发时 pipe 在第 0 步就停了。
"""
import re
import subprocess
import sys

from conftest import PIPE

PIPE_MD = (PIPE / "pipe.md").read_text(encoding="utf-8")
SCRIPTS = PIPE / "scripts"


def mock_rule() -> str:
    """CHALKBACK_MOCK=1 那条说明（可能跨行）。"""
    m = re.search(r"CHALKBACK_MOCK=1.*?(?=\n- |\n\n)", PIPE_MD, re.S)
    assert m, "pipe.md 里找不到 CHALKBACK_MOCK=1 的说明"
    return m.group(0)


def talks_to_screenpipe(path) -> bool:
    src = path.read_text(encoding="utf-8")
    return "SCREENPIPE_URL" in src or "extract_segments.search" in src


def test_every_screenpipe_script_is_covered_by_mock_rule():
    rule = mock_rule()
    scripts = sorted(p.name for p in SCRIPTS.glob("*.py") if talks_to_screenpipe(p))
    assert "doctor.py" in scripts and "lookback.py" in scripts
    missing = [s for s in scripts if s not in rule]
    assert not missing, f"这些脚本会连 screenpipe，但 pipe.md 的 mock 说明没提到：{missing}"


def test_each_script_supports_its_mock_flag():
    """说明的写法是“给 a.py、b.py 加 `--x`，给 c.py 加 `--y`”：逐句检查每个脚本支持分配给它的参数。"""
    clauses = re.findall(r"给(.*?)加\s*`(--[\w-]+)`", mock_rule(), re.S)
    assert clauses
    for scripts, flag in clauses:
        for script in re.findall(r"`(\w+\.py)`", scripts):
            help_text = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"],
                                       capture_output=True, text=True).stdout
            assert flag in help_text, f"{script} 不支持 {flag}"


def test_every_script_referenced_in_pipe_md_exists():
    for script in set(re.findall(r"scripts/(\w+\.py)", PIPE_MD)):
        assert (SCRIPTS / script).exists(), f"pipe.md 引用了不存在的脚本 {script}"


def test_every_flag_used_in_pipe_md_exists():
    """pipe.md 命令里的每个参数，脚本都必须认识。A 和 B 各自改脚本或 pipe.md 时，这里会发现接口不一致。"""
    for script, args in re.findall(r"scripts/(\w+\.py)([^\n`]*)", PIPE_MD):
        flags = set(re.findall(r"(?<![\w-])(--[a-z][\w-]*)", args))
        if not flags:
            continue
        help_text = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"],
                                   capture_output=True, text=True).stdout
        unknown = sorted(f for f in flags if f not in help_text)
        assert not unknown, f"pipe.md 给 {script} 传了它不认识的参数 {unknown}"
