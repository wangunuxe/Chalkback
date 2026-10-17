"""/setup：邀请码 → 学科班级 → 课表 → 知情同意（A1）→ 写 config.json 和 pipe 定时（TC2）。

审计：Hub 应记录 join 和 consent。pipe 定时：按课表生成 cron，POST screenpipe /pipes/chalkback/config。
"""
from fastapi import APIRouter

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("")
def setup_page():
    # TODO(TC2)
    return {"todo": "TC2 setup wizard"}
