"""tools/seed_mock_home.py: the generated fake ~/.chalkback/ must be as usable as pipe's real output."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_seeded_game_has_quiz_injected_without_answers(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "tools" / "seed_mock_home.py"), "--home", str(tmp_path)], check=True)
    quiz = json.loads((ROOT / "contracts" / "examples" / "quiz.json").read_text(encoding="utf-8"))
    out = tmp_path / "outbox" / quiz["lesson_id"]
    html = (out / "game.html").read_text(encoding="utf-8")

    assert (out / "ready").exists()
    assert "/*QUIZ_JSON*/ null" not in html, "the game page must have its questions injected by build_game.py"
    assert quiz["questions"][0]["prompt"] in html
    assert '"answer"' not in html and quiz["questions"][0]["source"]["quote"] not in html


def test_seed_keeps_mount_point_and_can_skip(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "stale.txt").write_text("old")
    seed = [sys.executable, str(ROOT / "tools" / "seed_mock_home.py"), "--home", str(home)]
    subprocess.run(seed, check=True)
    assert home.is_dir() and not (home / "stale.txt").exists()
    r = subprocess.run(seed + ["--if-empty"], check=True, capture_output=True, text=True)
    assert "skip" in r.stdout
