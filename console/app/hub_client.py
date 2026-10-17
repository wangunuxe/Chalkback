"""与学校 Hub 的通信（§6.4）。只有 coverage_share 和 join 请求会经过这里。"""
from __future__ import annotations

import httpx


class HubClient:
    def __init__(self, hub_url: str, token: str | None = None):
        self._http = httpx.Client(
            base_url=hub_url,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=10,
        )

    def join(self, invite_code: str, display_name: str, role: str = "teacher") -> dict:
        r = self._http.post("/api/join", json={"invite_code": invite_code, "display_name": display_name, "role": role})
        r.raise_for_status()
        return r.json()  # {teacher_id, token, workspace_id}

    def current_syllabus(self) -> dict:
        r = self._http.get("/api/syllabus/current")
        r.raise_for_status()
        return r.json()

    def share_coverage(self, coverage_share: dict) -> str:
        r = self._http.post("/api/coverage", json=coverage_share)
        r.raise_for_status()
        return r.json()["share_id"]

    def revoke(self, share_id: str) -> None:
        self._http.delete(f"/api/coverage/{share_id}").raise_for_status()

    def audit(self) -> list[dict]:
        r = self._http.get("/api/audit")
        r.raise_for_status()
        return r.json()
