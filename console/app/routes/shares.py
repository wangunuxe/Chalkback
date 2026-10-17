"""/shares：已上传记录（state/shares.json + Hub 审计）与撤回（A5）（TC6）。

TODO(C): shares.json 的格式技术文档未定义（§6.2 只列了文件名）。它只在 C 内部使用，由 C 自定并写进 console/README.md。
"""
from fastapi import APIRouter

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("")
def list_shares():
    # TODO(TC6)
    return {"shares": []}
