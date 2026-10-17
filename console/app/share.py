"""coverage -> coverage_share: the only coverage data allowed to leave the teacher's computer (§5, A3).

Fields are copied one by one from an allowlist rather than deleted from coverage -- so if coverage gains new fields later, they will not leak out.
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
