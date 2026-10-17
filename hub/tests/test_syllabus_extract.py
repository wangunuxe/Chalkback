"""Syllabus import: a file becomes a suggested draft; nothing is saved until the head uploads and approves it (A4).
The model call is replaced, so these tests need no API key and no network."""
import base64
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app import syllabus_extract
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)
TEACHER = {"Authorization": "Bearer mock-token-T1"}
HEAD = {"Authorization": "Bearer mock-token-H1"}
SCHEMA = Draft202012Validator(json.loads((ROOT / "contracts" / "syllabus.schema.json").read_text(encoding="utf-8")))

SYLLABUS_TEXT = """Programme de français, 4e

1. Le passé composé avec avoir
2. Le passé composé avec être
3. L'accord du participe passé
4. Le plus-que-parfait
"""


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def office(paths: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, xml in paths.items():
            z.writestr(name, xml)
    return buf.getvalue()


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def docx(lines):
    body = "".join(f"<w:p><w:r><w:t>{l}</w:t></w:r></w:p>" for l in lines)
    return office({"word/document.xml": f"<w:document {W}><w:body>{body}</w:body></w:document>"})


def pptx(slides):
    return office({f"ppt/slides/slide{i}.xml": f"<p:sld {A} xmlns:p='p'>"
                   + "".join(f"<a:p><a:r><a:t>{l}</a:t></a:r></a:p>" for l in lines) + "</p:sld>"
                   for i, lines in enumerate(slides, 1)})


def model_answer(**over):
    """What the model returns for SYLLABUS_TEXT: the first three match the approved KP01–KP03, the last is new."""
    answer = {"subject": "Français", "level": "4e", "knowledge_points": [
        {"title": "Le passé composé avec avoir", "keywords": ["avoir", "participe passé", "avoir"], "existing_kp_id": "KP01"},
        {"title": "Le passé composé avec être", "keywords": ["être", "verbes de mouvement"], "existing_kp_id": "KP02"},
        {"title": "Accord du participe passé", "keywords": ["accord", "COD placé avant"], "existing_kp_id": "KP03"},
        {"title": "Le plus-que-parfait", "keywords": ["plus-que-parfait", "avais"], "existing_kp_id": None},
    ]}
    return {**answer, **over}


@pytest.fixture
def model(monkeypatch):
    """Records what was sent to the model; returns model_answer() unless a test sets calls.answer."""
    class Calls(list):
        answer = None
    calls = Calls()

    def fake(content):
        calls.append(content)
        return calls.answer(len(calls)) if callable(calls.answer) else (calls.answer or model_answer())
    monkeypatch.setattr(syllabus_extract, "call_model", fake)
    return calls


def post(filename, data, headers=HEAD, **extra):
    return client.post("/api/syllabus/extract", headers=headers,
                       json={"filename": filename, "content_base64": b64(data), **extra})


def current():
    return client.get("/api/syllabus/current", headers=TEACHER).json()


def test_text_file_becomes_a_valid_draft_and_keeps_existing_ids(model):
    before = current()
    r = post("programme.txt", SYLLABUS_TEXT.encode())
    assert r.status_code == 200, r.text
    body = r.json()
    draft = body["syllabus"]
    SCHEMA.validate(draft)
    assert draft["syllabus_id"] == before["syllabus_id"] and draft["status"] == "draft"
    assert [kp["kp_id"] for kp in draft["knowledge_points"]] == ["KP01", "KP02", "KP03", "KP05"]  # KP04 not reused
    assert body["kept"] == ["KP01", "KP02", "KP03"] and body["new"] == ["KP05"] and body["dropped"] == ["KP04"]
    assert draft["knowledge_points"][0]["keywords"] == ["avoir", "participe passé"]  # duplicates removed
    # The model saw the document and the existing points
    sent = json.dumps(model[0], ensure_ascii=False)
    assert "Le plus-que-parfait" in sent and "KP04: L'imparfait" in sent


def test_extract_saves_nothing(model):
    before = current()
    post("programme.txt", SYLLABUS_TEXT.encode())
    assert current() == before
    drafts = client.get("/api/dashboard?view=head", headers=HEAD).json()["drafts"]
    # the suggestion is then uploaded through the normal draft flow
    assert client.post("/api/syllabus", json=post("programme.txt", SYLLABUS_TEXT.encode()).json()["syllabus"],
                       headers=HEAD).status_code == 200
    assert len(client.get("/api/dashboard?view=head", headers=HEAD).json()["drafts"]) >= len(drafts)
    assert current() == before


def test_docx_and_pptx_text_is_read(model):
    assert post("programme.docx", docx(["Programme 4e", "Le plus-que-parfait"])).status_code == 200
    assert "Le plus-que-parfait" in model[-1][0]["text"]
    assert post("cours.pptx", pptx([["Titre"], ["Le passé composé", "avec être"]])).status_code == 200
    text = model[-1][0]["text"]
    assert "[Slide 2]" in text and "avec être" in text


def test_pdf_is_sent_as_a_document(model):
    pdf = b"%PDF-1.4 fake"
    assert post("programme.pdf", pdf).status_code == 200
    doc = model[-1][0]
    assert doc["type"] == "document" and base64.b64decode(doc["source"]["data"]) == pdf


def test_long_text_is_chunked_and_merged(model, monkeypatch):
    monkeypatch.setattr(syllabus_extract, "CHUNK_CHARS", 60)
    model.answer = lambda n: model_answer(knowledge_points=[
        {"title": "Le passé composé avec être", "keywords": [f"mot{n}"], "existing_kp_id": "KP02"},
        {"title": f"Point {n}", "keywords": [], "existing_kp_id": None},
    ])
    r = post("long.md", SYLLABUS_TEXT.encode())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chunks"] == len(model) > 1
    points = body["syllabus"]["knowledge_points"]
    titles = [kp["title"] for kp in points]
    assert titles.count("Le passé composé avec être") == 1           # same point in several chunks → once
    assert points[0]["keywords"] == [f"mot{i}" for i in range(1, len(model) + 1)]
    assert "part 1 of" in model[0][1]["text"]


def test_existing_id_given_twice_is_only_kept_once(model):
    model.answer = model_answer(knowledge_points=[
        {"title": "A", "keywords": [], "existing_kp_id": "KP01"},
        {"title": "B", "keywords": [], "existing_kp_id": "KP01"},
        {"title": "C", "keywords": [], "existing_kp_id": "KP99"},     # not an existing id
    ])
    ids = [kp["kp_id"] for kp in post("p.txt", b"x").json()["syllabus"]["knowledge_points"]]
    assert ids == ["KP01", "KP05", "KP06"]


CHINOIS = model_answer(subject="Chinois", level="Collège", knowledge_points=[
    {"title": "Salutations et présentations", "keywords": ["你好"], "existing_kp_id": "KP01"},  # matched to a French point
    {"title": "L'école en Chine", "keywords": [], "existing_kp_id": None},
])


def test_other_subject_becomes_a_separate_syllabus(model):
    main = current()
    model.answer = CHINOIS
    body = post("chinois.pdf", b"%PDF").json()
    draft = body["syllabus"]
    assert body["subject_changed"] is True and body["new_syllabus"] is True
    assert body["previous_subject"] == main["subject"]
    assert draft["syllabus_id"] == "chinois-college"
    assert [kp["kp_id"] for kp in draft["knowledge_points"]] == ["KP01", "KP02"]  # its own numbering
    assert body["kept"] == [] and body["dropped"] == []

    # Uploading and approving it adds a syllabus; the school's main syllabus is unchanged
    assert client.post("/api/syllabus", json=draft, headers=HEAD).status_code == 200
    drafts = client.get("/api/dashboard?view=head", headers=HEAD).json()["drafts"]
    assert {"syllabus_id": "chinois-college", "version": 1} in drafts       # shown to approve, though v1 ≤ main's version
    assert client.post("/api/syllabus/chinois-college/approve", headers=HEAD).status_code == 200
    drafts = client.get("/api/dashboard?view=head", headers=HEAD).json()["drafts"]
    assert not any(d["syllabus_id"] == "chinois-college" for d in drafts)
    assert current() == main
    assert "chinois-college" in [s["syllabus_id"] for s in client.get("/api/syllabus", headers=TEACHER).json()]

    # Next import for that subject is a new version of it; identical titles keep their id
    model.answer = model_answer(subject="Chinois", level="Collège", knowledge_points=[
        {"title": "L'école en Chine", "keywords": [], "existing_kp_id": None},
        {"title": "Les fêtes chinoises", "keywords": [], "existing_kp_id": None},
    ])
    again = post("chinois-v2.pdf", b"%PDF").json()
    assert again["syllabus"]["syllabus_id"] == "chinois-college" and again["new_syllabus"] is False
    assert [kp["kp_id"] for kp in again["syllabus"]["knowledge_points"]] == ["KP02", "KP03"]
    assert again["dropped"] == ["KP01"]


def test_same_subject_is_not_flagged(model):
    model.answer = model_answer(subject="  FRANÇAIS ")
    assert post("programme.txt", b"x").json()["subject_changed"] is False


def test_chunk_text_never_exceeds_limit():
    text = "\n\n".join(["a" * 30, "b" * 30, "c" * 150, "d"])
    chunks = syllabus_extract.chunk_text(text, max_chars=60)
    assert all(len(c) <= 60 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_teacher_cannot_extract(model):
    assert post("programme.txt", b"x", headers=TEACHER).status_code == 403
    assert model == []


@pytest.mark.parametrize("filename,data,status", [
    ("notes.xlsx", b"x", 415),
    ("programme.txt", b"", 422),
    ("programme.docx", b"not a zip", 422),
])
def test_bad_files_rejected(model, filename, data, status):
    assert post(filename, data).status_code == status
    assert model == []


def test_too_large_rejected(model, monkeypatch):
    monkeypatch.setattr(syllabus_extract, "MAX_BYTES", 10)
    assert post("programme.txt", b"x" * 11).status_code == 413


def test_no_points_found(model):
    model.answer = model_answer(knowledge_points=[])
    r = post("programme.txt", b"Calendrier des examens")
    assert r.status_code == 422 and "No knowledge points" in r.json()["detail"]


@pytest.fixture
def no_ai_env(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "HUB_AI_PROVIDER", "HUB_AI_MODEL"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture
def http(no_ai_env):
    """Replaces httpx.post: records the request, answers like the provider would."""
    sent = {}

    class Reply:
        status_code = 200

        @staticmethod
        def json():
            if "anthropic" in sent["url"]:
                return {"content": [{"type": "tool_use", "name": "record_syllabus", "input": model_answer()}]}
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(model_answer())}]}}]}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, body=json, headers=headers)
        return Reply()
    no_ai_env.setattr(syllabus_extract.httpx, "post", fake_post)
    return sent


def test_without_api_key_says_not_configured(no_ai_env):
    r = post("programme.txt", SYLLABUS_TEXT.encode())
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]


def test_claude_request_is_forced_to_the_tool(http, no_ai_env):
    no_ai_env.setenv("ANTHROPIC_API_KEY", "test-key")
    assert post("programme.txt", SYLLABUS_TEXT.encode()).status_code == 200
    assert http["url"].startswith("https://api.anthropic.com/")
    assert http["headers"]["x-api-key"] == "test-key"
    assert http["body"]["model"] == "claude-opus-5-5"
    assert http["body"]["tool_choice"] == {"type": "tool", "name": "record_syllabus"}


def test_gemini_used_with_a_gemini_key(http, no_ai_env):
    no_ai_env.setenv("GEMINI_API_KEY", "g-key")
    no_ai_env.setenv("HUB_AI_MODEL", "gemini-3.1-flash-lite")
    r = post("programme.pdf", b"%PDF-1.4 fake")
    assert r.status_code == 200, r.text
    assert [kp["kp_id"] for kp in r.json()["syllabus"]["knowledge_points"]] == ["KP01", "KP02", "KP03", "KP05"]
    assert http["url"].endswith("/models/gemini-3.1-flash-lite:generateContent")
    assert http["headers"] == {"x-goog-api-key": "g-key"}
    parts = http["body"]["contents"][0]["parts"]
    assert parts[0]["inline_data"]["mime_type"] == "application/pdf" and "text" in parts[1]
    schema = http["body"]["generationConfig"]["responseSchema"]
    kp = schema["properties"]["knowledge_points"]["items"]
    assert kp["properties"]["existing_kp_id"] == {"type": "STRING", "nullable": True, "description": kp["properties"]["existing_kp_id"]["description"]}
    assert "additionalProperties" not in json.dumps(schema)


def test_claude_first_unless_provider_forced(http, no_ai_env):
    no_ai_env.setenv("ANTHROPIC_API_KEY", "a-key")
    no_ai_env.setenv("GEMINI_API_KEY", "g-key")
    post("programme.txt", b"x")
    assert "anthropic" in http["url"]
    no_ai_env.setenv("HUB_AI_PROVIDER", "gemini")
    post("programme.txt", b"x")
    assert "googleapis" in http["url"] and "gemini-flash-latest" in http["url"]


def test_gemini_bad_reply_is_502(no_ai_env):
    class Reply:
        status_code = 200
        json = staticmethod(lambda: {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]})
    no_ai_env.setenv("GEMINI_API_KEY", "g-key")
    no_ai_env.setattr(syllabus_extract.httpx, "post", lambda *a, **k: Reply())
    assert post("programme.txt", b"x").status_code == 502
