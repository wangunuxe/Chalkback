"""coverage → coverage_share：唯一允许离开老师电脑的覆盖数据（§5，A3）。

用白名单逐字段复制，而不是从 coverage 里删字段——这样 coverage 以后多了字段也不会被带出去。
"""
from __future__ import annotations

from datetime import datetime


def to_coverage_share(coverage: dict) -> dict:
    return {
        "lesson_id": coverage["lesson_id"],
        "class_id": coverage["class_id"],
        "date": datetime.strptime(coverage["lesson_id"].split("-")[2], "%Y%m%d").date().isoformat(),
        "syllabus_id": coverage["syllabus_id"],
        "syllabus_version": coverage["syllabus_version"],
        "points": [
            {"kp_id": p["kp_id"], "covered": p["covered"], "minutes": p["minutes"]}
            for p in coverage["points"]
        ],
    }
