"""与学校 Hub 的通信（§6.4）。只有 coverage_share 和 join 请求会经过这里。"""
from __future__ import annotations

import httpx
from fastapi import HTTPException

from . import paths
from .contracts import read_json


class HubClient:
    def __init__(self, hub_url: str, token: str | None = None):
        self._http = httpx.Client(
            base_url=hub_url,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=10,
            verify=False if hub_url.startswith("https://") else True,
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
        """撤回（A5）。Hub 上已经不存在（404）也算撤回成功。"""
        r = self._http.delete(f"/api/coverage/{share_id}")
        if r.status_code != 404:
            r.raise_for_status()

    def audit(self) -> list[dict]:
        r = self._http.get("/api/audit")
        r.raise_for_status()
        return r.json()


def from_config() -> HubClient:
    """用 config.json 里的 hub_url 和 token。没完成 /setup 就不能和 Hub 通信，不回落到 mock token。"""
    cfg = read_json(paths.CONFIG)
    if not cfg or not cfg.get("hub_url") or not cfg.get("token"):
        raise HTTPException(409, "Not set up yet: complete /setup first")
    return HubClient(cfg["hub_url"], cfg["token"])


def hub_error(e: Exception) -> HTTPException:
    """Hub 不通或拒绝时，如实告诉老师，不假装成功。"""
    if isinstance(e, httpx.HTTPStatusError):
        return HTTPException(502, f"Hub refused the request ({e.response.status_code}): {e.response.text[:200]}")
    return HTTPException(502, f"Hub unreachable: {e}")
