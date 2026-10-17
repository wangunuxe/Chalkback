"""/shares：已上传记录（state/shares.json）与撤回（A5）（TC6）。

state/shares.json 格式：[{share_id, lesson_id, class_id, shared_at}]，每节课最多一条（重传替换）。
撤回时先让 Hub 删除；Hub 删除成功（或 Hub 上已不存在）才删本机记录，否则返回 502，记录保留。
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
