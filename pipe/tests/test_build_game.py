import json
import re
import shutil
import subprocess

import pytest

from build_game import PLACEHOLDER, TEMPLATE, leaks, main, public_quiz, render
from conftest import example


def test_public_quiz_strips_answers_and_sources():
    pub = public_quiz(example("quiz"))
    for q in pub["questions"]:
        assert set(q) <= {"q_id", "type", "prompt", "choices", "time_limit_s"}
    assert pub["questions"][0]["choices"] == example("quiz")["questions"][0]["choices"]


def test_rendered_page_has_no_leaks():
    quiz = example("quiz")
    html = render(TEMPLATE.read_text(encoding="utf-8"), quiz)
    assert PLACEHOLDER not in html
    assert leaks(html, quiz) == []
    assert quiz["questions"][0]["prompt"] in html


def test_leak_detected_when_template_contains_quote():
    quiz = example("quiz")
    html = render(f"<script>const QUIZ = {PLACEHOLDER};</script>" + quiz["questions"][0]["source"]["quote"], quiz)
    assert leaks(html, quiz)


def test_script_breakout_escaped():
    quiz = example("quiz")
    quiz["questions"][0]["prompt"] = "</script><script>alert(1)</script>"
    html = render(f"<script>const QUIZ = {PLACEHOLDER};</script>", quiz)
    assert html.count("</script>") == 1


def test_template_must_have_one_placeholder():
    with pytest.raises(ValueError):
        render("<html></html>", example("quiz"))


def test_cli_writes_file(write_json, tmp_path):
    out = tmp_path / "game.html"
    assert main(["--quiz", str(write_json("quiz.json", example("quiz"))), "--out", str(out)]) == 0
    assert out.exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="node is needed to check JS syntax")
def test_generated_javascript_parses(tmp_path):
    html = render(TEMPLATE.read_text(encoding="utf-8"), example("quiz"))
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    js = tmp_path / "game.js"
    js.write_text(script, encoding="utf-8")
    subprocess.run(["node", "--check", str(js)], check=True)


# Template regression checks: PR #3 once replaced the template with a look-only static mockup; the checks below catch that kind of change before merge.

def template_script() -> str:
    return re.search(r"<script>(.*)</script>", TEMPLATE.read_text(encoding="utf-8"), re.S).group(1)


def test_template_loads_nothing_from_the_internet():
    """Students' phones connect to the teacher's computer and the school network may have no internet: no CDNs, web fonts or external images."""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert not re.search(r"(src|href)\s*=\s*[\"']?(https?:)?//", html, re.I)
    assert not re.search(r"@import|url\(\s*[\"']?(https?:)?//", html, re.I)
    assert "<script src" not in html and "<link" not in html


def test_template_actually_plays_the_quiz():
    js = template_script()
    assert "QUIZ.questions" in js, "must render the injected questions, not hard-coded ones"
    assert "/attempt" in js and "fetch(" in js, "must submit attempts to the console"
    assert "time_limit_s" in js, "must time each question by its time limit"
    for kind in ("mcq", "true_false"):
        assert f'"{kind}"' in js, f"must support {kind}"
    assert "alert(" not in js and "innerHTML" not in js, "feedback must use page elements; question text may only use textContent"
