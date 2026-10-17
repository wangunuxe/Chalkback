"""Syllabus import: a department head uploads a syllabus file, the LLM proposes the knowledge points (the only LLM call in the Hub).

The result is only a suggestion that fills the dashboard's draft form. Nothing is saved here: the head checks and edits it,
then the usual flow applies (POST /api/syllabus → draft → approve, A4). The file is not stored.

Split of work (same principle as the pipe, DESIGN.md §3): the model judges what the knowledge points are and whether one
is the same as an existing point; this module does the fixed logic: reading the file, chunking long text, merging chunks,
assigning kp_ids (existing ids are kept, so past coverage data still matches) and schema validation.

Configuration (in .env, never in the repo): ANTHROPIC_API_KEY for Claude or GEMINI_API_KEY for Gemini (Claude first if both
are set; HUB_AI_PROVIDER=anthropic|gemini forces one), HUB_AI_MODEL (default per provider, see DEFAULT_MODELS).
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import os
import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import httpx
from jsonschema import Draft202012Validator

from .mock import EXAMPLES

MAX_BYTES = 5 * 1024 * 1024
CHUNK_CHARS = 60_000          # roughly 15k tokens; a normal syllabus fits in one chunk
MAX_CHUNKS = 8
MAX_KEYWORDS = 8
DEFAULT_MODELS = {"anthropic": "claude-opus-5-5", "gemini": "gemini-flash-latest"}
KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}
API_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 180

SCHEMA = Draft202012Validator(json.loads((EXAMPLES.parent / "syllabus.schema.json").read_text(encoding="utf-8")))

TEXT_TYPES = {".txt", ".md"}
SUPPORTED = {".pdf", ".docx", ".pptx", *TEXT_TYPES}


class ExtractError(Exception):
    """Error shown to the head; status is the HTTP status the route returns."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------- reading the file ----------

def decode_upload(filename: str, content_base64: str) -> tuple[str, bytes]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise ExtractError(415, f"Unsupported file type {suffix or '(none)'}; use PDF, DOCX, PPTX, TXT or MD.")
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise ExtractError(422, "The file content is not valid base64.")
    if not data:
        raise ExtractError(422, "The file is empty.")
    if len(data) > MAX_BYTES:
        raise ExtractError(413, f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    return suffix, data


def _xml_texts(xml: bytes, paragraph_tag: str, text_tag: str) -> list[str]:
    """Text of each paragraph in an Office XML part (namespace-agnostic)."""
    root = ElementTree.fromstring(xml)
    lines = []
    for p in root.iter():
        if p.tag.rsplit("}", 1)[-1] != paragraph_tag:
            continue
        line = "".join(t.text or "" for t in p.iter() if t.tag.rsplit("}", 1)[-1] == text_tag).strip()
        if line:
            lines.append(line)
    return lines


def office_text(suffix: str, data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if suffix == ".docx":
                return "\n".join(_xml_texts(z.read("word/document.xml"), "p", "t"))
            slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                            key=lambda n: int(re.search(r"\d+", n).group()))
            return "\n\n".join(f"[Slide {i}]\n" + "\n".join(_xml_texts(z.read(n), "p", "t"))
                               for i, n in enumerate(slides, 1))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
        raise ExtractError(422, f"Could not read this {suffix.upper().lstrip('.')} file.")


def file_text(suffix: str, data: bytes) -> str:
    if suffix in TEXT_TYPES:
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("latin-1")
    return office_text(suffix, data)


def chunk_text(text: str, max_chars: int | None = None) -> list[str]:
    """Pack paragraphs into chunks of at most max_chars, never cutting a paragraph unless it is longer than a chunk."""
    max_chars = max_chars or CHUNK_CHARS
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= max_chars:
        return [text] if text else []
    chunks, current = [], ""
    for para in text.split("\n\n"):
        while len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if current and len(current) + 2 + len(para) > max_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


# ---------- the model ----------

TOOL = {
    "name": "record_syllabus",
    "description": "Record the knowledge points found in the syllabus document.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["subject", "level", "knowledge_points"],
        "properties": {
            "subject": {"type": "string", "description": "School subject, e.g. Français"},
            "level": {"type": "string", "description": "Grade or level, e.g. 4e"},
            "knowledge_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "keywords", "existing_kp_id"],
                    "properties": {
                        "title": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "existing_kp_id": {"type": ["string", "null"],
                                           "description": "kp_id of the existing point this is the same as, or null"},
                    },
                },
            },
        },
    },
}

SYSTEM = """You turn a school syllabus document into the knowledge point list used by ChalkBack.
ChalkBack matches what a teacher said and showed in class against these points, writes quiz questions for the points
that were covered, and tells the department which points each class has not covered yet.

Rules:
- A knowledge point is one teachable, testable unit that takes one or a few lessons (e.g. "Le passé composé avec être").
  Not a whole chapter, not a single example sentence.
- Only points the document actually lists. Do not add points from your own knowledge of the subject.
- Skip administrative content: dates, grading, materials, general aims, assessment calendars.
- title: short (at most about 80 characters), in the document's language, worded as in the document.
- keywords: 3 to 6 words or short phrases a teacher would actually say or put on a slide when teaching this point,
  in the language of instruction. Prefer terms that appear in the document. They are used for full-text search,
  so avoid generic words ("grammaire", "exercice") that would match every lesson.
- Keep the order of the document.
- existing_kp_id: the existing points are listed below. If a point is the same knowledge point as an existing one
  (even if worded differently), give that kp_id; otherwise null. Never give the same existing kp_id to two points.
- subject and level: from the document; if it does not say, reuse the current ones given below.
Call record_syllabus exactly once."""


def _prompt(existing: dict | None, part: int, parts: int) -> str:
    current = existing or {"subject": "", "level": "", "knowledge_points": []}
    lines = [f"Current subject: {current['subject'] or '(none)'}", f"Current level: {current['level'] or '(none)'}",
             "Existing knowledge points:"]
    lines += [f"- {kp['kp_id']}: {kp['title']}" for kp in current["knowledge_points"]] or ["(none)"]
    if parts > 1:
        lines.append(f"\nThis is part {part} of {parts} of a long document: list only the points in this part.")
    return "\n".join(lines)


def provider() -> tuple[str, str]:
    """(provider, api key). Claude first if both keys are set, unless HUB_AI_PROVIDER says otherwise."""
    forced = os.environ.get("HUB_AI_PROVIDER", "").strip().lower()
    for name in ([forced] if forced in KEY_VARS else ["anthropic", "gemini"]):
        key = os.environ.get(KEY_VARS[name], "").strip()
        if key:
            return name, key
    raise ExtractError(503, "AI import is not configured on this Hub (set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env). "
                            "Add the points by hand.")


def _post(url: str, body: dict, headers: dict) -> dict:
    try:
        r = httpx.post(url, json=body, timeout=TIMEOUT, headers=headers)
    except httpx.HTTPError as e:
        raise ExtractError(502, f"Could not reach the AI service ({type(e).__name__}).")
    if r.status_code != 200:
        raise ExtractError(502, f"The AI service returned an error ({r.status_code}).")
    return r.json()


def _call_anthropic(content: list[dict], key: str, model: str) -> dict:
    body = {
        "model": model,
        "max_tokens": 8000,
        "system": SYSTEM,
        "tools": [TOOL],
        "tool_choice": {"type": "tool", "name": TOOL["name"]},
        "messages": [{"role": "user", "content": content}],
    }
    reply = _post(API_URL, body, {"x-api-key": key, "anthropic-version": "2023-06-01"})
    for block in reply.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == TOOL["name"]:
            return block["input"]
    raise ExtractError(502, "The AI service did not return a knowledge point list.")


def _gemini_schema(schema: dict) -> dict:
    """JSON Schema of TOOL → Gemini responseSchema (OpenAPI subset: no additionalProperties, nullable instead of type lists)."""
    out = {k: v for k, v in schema.items() if k in ("description", "required")}
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    out["type"] = next(t for t in types if t != "null").upper()
    if "null" in types:
        out["nullable"] = True
    if "properties" in schema:
        out["properties"] = {k: _gemini_schema(v) for k, v in schema["properties"].items()}
        out["propertyOrdering"] = list(schema["properties"])
    if "items" in schema:
        out["items"] = _gemini_schema(schema["items"])
    return out


def _gemini_part(block: dict) -> dict:
    if block["type"] == "document":
        return {"inline_data": {"mime_type": block["source"]["media_type"], "data": block["source"]["data"]}}
    return {"text": block["text"]}


def _call_gemini(content: list[dict], key: str, model: str) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM.replace("Call record_syllabus exactly once.", "Answer with the JSON only.")}]},
        "contents": [{"role": "user", "parts": [_gemini_part(b) for b in content]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "responseSchema": _gemini_schema(TOOL["input_schema"])},
    }
    reply = _post(GEMINI_URL.format(model=model), body, {"x-goog-api-key": key})
    try:
        text = "".join(p.get("text", "") for p in reply["candidates"][0]["content"]["parts"])
        return json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise ExtractError(502, "The AI service did not return a knowledge point list.")


def call_model(content: list[dict]) -> dict:
    """One model call; content uses Anthropic's block format (text / PDF document). Returns the record_syllabus input.
    Tests replace this function."""
    name, key = provider()
    model = os.environ.get("HUB_AI_MODEL", "").strip() or DEFAULT_MODELS[name]
    return (_call_anthropic if name == "anthropic" else _call_gemini)(content, key, model)


def ask_model(suffix: str, data: bytes, existing: dict | None) -> tuple[list[dict], int]:
    """Returns (model outputs, number of chunks). PDFs go to the model as documents (layout and tables kept)."""
    if suffix == ".pdf":
        doc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                              "data": base64.b64encode(data).decode()}}
        return [call_model([doc, {"type": "text", "text": _prompt(existing, 1, 1)}])], 1
    chunks = chunk_text(file_text(suffix, data))
    if not chunks:
        raise ExtractError(422, "No text found in this file.")
    if len(chunks) > MAX_CHUNKS:
        raise ExtractError(413, "The document is too long; upload only the part with the knowledge points.")
    return [call_model([{"type": "text", "text": f"<document>\n{c}\n</document>"},
                        {"type": "text", "text": _prompt(existing, i, len(chunks))}])
            for i, c in enumerate(chunks, 1)], len(chunks)


# ---------- fixed logic after the model ----------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().casefold()


def _clean_keywords(words) -> list[str]:
    out, seen = [], set()
    for w in words or []:
        w = re.sub(r"\s+", " ", str(w)).strip()
        if w and _norm(w) not in seen:
            seen.add(_norm(w))
            out.append(w)
    return out[:MAX_KEYWORDS]


def build_draft(outputs: list[dict], existing: dict | None, syllabus_id: str) -> dict:
    """Merge the chunks, keep existing kp_ids, number new points after the highest existing id, validate."""
    existing_ids = {kp["kp_id"] for kp in (existing or {}).get("knowledge_points", [])}
    merged: dict[str, dict] = {}
    for out in outputs:
        for kp in out.get("knowledge_points", []):
            title = re.sub(r"\s+", " ", str(kp.get("title", ""))).strip()
            if not title:
                continue
            key = _norm(title)
            if key in merged:   # the same point found in two chunks
                merged[key]["keywords"] = _clean_keywords(merged[key]["keywords"] + list(kp.get("keywords") or []))
                merged[key]["existing"] = merged[key]["existing"] or kp.get("existing_kp_id")
            else:
                merged[key] = {"title": title, "keywords": _clean_keywords(kp.get("keywords")),
                               "existing": kp.get("existing_kp_id")}
    if not merged:
        raise ExtractError(422, "No knowledge points were found in this file.")

    used: set[str] = set()
    points = []
    for p in merged.values():
        kp_id = p["existing"] if p["existing"] in existing_ids and p["existing"] not in used else None
        if kp_id:
            used.add(kp_id)
        points.append({"kp_id": kp_id, "title": p["title"], "keywords": p["keywords"]})
    numbers = [int(m.group()) for i in existing_ids if (m := re.search(r"\d+", i))]
    width = max([len(m.group()) for i in existing_ids if (m := re.search(r"\d+", i))] or [2])
    nxt = max(numbers or [0]) + 1
    for p in points:
        if p["kp_id"] is None:
            p["kp_id"] = f"KP{nxt:0{width}d}"
            nxt += 1

    first = outputs[0] if outputs else {}
    draft = {
        "syllabus_id": syllabus_id,
        "version": 1,
        "status": "draft",
        "subject": str(first.get("subject") or "").strip() or (existing or {}).get("subject", ""),
        "level": str(first.get("level") or "").strip() or (existing or {}).get("level", ""),
        "knowledge_points": points,
    }
    errors = [e.message for e in SCHEMA.iter_errors(draft)]
    if errors:
        raise ExtractError(422, "The AI suggestion is not a valid syllabus: " + "; ".join(errors[:3]))
    return draft


def extract(filename: str, content_base64: str, existing: dict | None, syllabus_id: str) -> dict:
    suffix, data = decode_upload(filename, content_base64)
    outputs, chunks = ask_model(suffix, data, existing)
    draft = build_draft(outputs, existing, syllabus_id)
    old = {kp["kp_id"] for kp in (existing or {}).get("knowledge_points", [])}
    kept = [kp["kp_id"] for kp in draft["knowledge_points"] if kp["kp_id"] in old]
    return {
        "syllabus": draft,
        "chunks": chunks,
        "kept": kept,
        "new": [kp["kp_id"] for kp in draft["knowledge_points"] if kp["kp_id"] not in old],
        "dropped": sorted(old - set(kept)),
    }
