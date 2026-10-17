"""/shares：已上传记录（state/shares.json + Hub 审计）与撤回（A5）（TC6）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import paths
from ..hub_client import HubClient

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("")
def list_shares():
    shares = []
    if paths.SHARES.exists():
        try:
            shares = json.loads(paths.SHARES.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"shares": shares}


@router.delete("/{share_id}")
def withdraw_share(share_id: str):
    shares = []
    if paths.SHARES.exists():
        try:
            shares = json.loads(paths.SHARES.read_text(encoding="utf-8"))
        except Exception:
            pass

    target = next((s for s in shares if s.get("share_id") == share_id), None)
    if not target:
        raise HTTPException(404, "Share record not found")

    # Try revoking on Hub
    hub_url = "https://localhost:8443"
    token = None
    if paths.CONFIG.exists():
        try:
            cfg = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
            hub_url = cfg.get("hub_url", hub_url)
            token = cfg.get("token")
        except Exception:
            pass

    try:
        client = HubClient(hub_url=hub_url, token=token)
        client.revoke(share_id)
    except Exception as e:
        print(f"Hub revoke offline fallback: {e}")

    # Remove from shares.json
    shares = [s for s in shares if s.get("share_id") != share_id]
    try:
        paths.SHARES.parent.mkdir(parents=True, exist_ok=True)
        paths.SHARES.write_text(json.dumps(shares, ensure_ascii=False, indent=2), encoding="utf-8")

        # Log edit event
        edit_event = {
            "type": "withdraw_share",
            "share_id": share_id,
            "at": datetime.now(timezone.utc).isoformat()
        }
        with open(paths.EDITS, "a", encoding="utf-8") as f:
            f.write(json.dumps(edit_event, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(500, f"Failed to record withdrawal: {e}")

    return {"status": "success", "withdrawn_share_id": share_id}
