"""极简的假 screenpipe：GET /search，返回格式按 demo/screenpipe_test_record.md（H2 实测）。

支持 content_type、q（不区分大小写的子串）、start_time、end_time、limit、offset；记录收到的每个请求的参数。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def audio(tid: int, text: str, ts: str, device_type: str = "input") -> dict:
    return {"type": "Audio", "content": {"audio_transcription_id": tid, "transcription": text, "timestamp": ts,
                                         "audio_chunk_id": tid, "offset_index": 0, "device": "Mic",
                                         "device_type": device_type, "speaker": None}}


def ocr(frame_id: int, text: str, ts: str, app: str = "PowerPoint", window: str = "cours.pptx") -> dict:
    return {"type": "OCR", "content": {"frame_id": frame_id, "text": text, "timestamp": ts,
                                       "app_name": app, "window_name": window}}


class FakeScreenpipe:
    def __init__(self, items: list[dict]):
        self.items = items
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                url = urlparse(self.path)
                params = {k: v[0] for k, v in parse_qs(url.query).items()}
                fake.requests.append(params)
                body = json.dumps(fake.search(params)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def search(self, p: dict) -> dict:
        kind = {"audio": "Audio", "ocr": "OCR"}.get(p.get("content_type"))
        start = datetime.fromisoformat(p["start_time"]) if "start_time" in p else None
        end = datetime.fromisoformat(p["end_time"]) if "end_time" in p else None
        out = []
        for item in self.items:
            c = item["content"]
            text = c.get("transcription") or c.get("text") or ""
            at = datetime.fromisoformat(c["timestamp"])
            if kind and item["type"] != kind:
                continue
            if "q" in p and p["q"].casefold() not in text.casefold():
                continue
            if (start and at < start) or (end and at > end):
                continue
            out.append(item)
        offset, limit = int(p.get("offset", 0)), int(p.get("limit", 20))
        page = out[offset:offset + limit]
        return {"data": page, "pagination": {"limit": limit, "offset": offset, "total": len(out)}}

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
