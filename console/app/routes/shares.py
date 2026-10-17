"""/shares: upload records (state/shares.json) and withdrawal (A5) (TC6).

state/shares.json format: [{share_id, lesson_id, class_id, shared_at}], at most one per lesson (re-uploading replaces it).
To withdraw, first ask the Hub to delete; only when the Hub delete succeeds (or the share no longer exists on the Hub) is the local record removed; otherwise return 502 and keep the record.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import paths
from ..contracts import read_json, write_json
from ..hub_client import from_config, hub_error

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("")
def list_shares():
    return {"shares": read_json(paths.SHARES, [])}


@router.delete("/{share_id}")
def withdraw_share(share_id: str):
    shares = read_json(paths.SHARES, [])
    if not any(s["share_id"] == share_id for s in shares):
        raise HTTPException(404, "Share record not found")

    client = from_config()
    try:
        client.revoke(share_id)
    except Exception as e:
        raise hub_error(e)

    write_json(paths.SHARES, [s for s in shares if s["share_id"] != share_id])
    return {"status": "withdrawn", "share_id": share_id}
