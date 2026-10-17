"""往正在运行的 Hub 灌演示覆盖数据（TD6 彩排、截图用）。

    python hub/scripts/seed_demo.py [https://localhost:8443]

走真实的 POST /api/coverage（与 C 的控制台上传同一路径），用 mock token：
- T1 → 4A：进度正常（与控制台的 mock 老师 T1 是同一个身份）
- T2 → 4B：开学后只讲了 1 个知识点 → 触发“考前讲不完”
- T2 → 4C：讲了 KP02，T1 的老师视图会看到“别的班讲了、你还没讲”
知识点按 contracts/examples/syllabus.json（KP01–KP04）。演示考纲（H4）定稿后同步修改。
"""
import sys

import httpx

LESSONS = [
    ("T1", "4A", "2026-09-14", {"KP01": 6.0}),
    ("T1", "4A", "2026-10-17", {"KP03": 4.5}),
    ("T2", "4B", "2026-09-01", {"KP01": 5.0}),
    ("T2", "4C", "2026-09-03", {"KP01": 4.0}),
    ("T2", "4C", "2026-09-24", {"KP02": 7.5}),
    ("T2", "4C", "2026-10-15", {"KP04": 3.0}),
]


def main(hub: str) -> None:
    with httpx.Client(base_url=hub, verify=False) as client:  # 本地 Hub 用自签名证书
        syllabus = client.get("/api/syllabus/current", headers={"Authorization": "Bearer mock-token-T1"}).json()
        for teacher, class_id, day, minutes in LESSONS:
            body = {
                "lesson_id": f"L-{teacher}-{day.replace('-', '')}-1000",
                "class_id": class_id,
                "date": day,
                "syllabus_id": syllabus["syllabus_id"],
                "syllabus_version": syllabus["version"],
                "points": [{"kp_id": kp["kp_id"], "covered": kp["kp_id"] in minutes,
                            "minutes": minutes.get(kp["kp_id"], 0)} for kp in syllabus["knowledge_points"]],
            }
            r = client.post("/api/coverage", json=body, headers={"Authorization": f"Bearer mock-token-{teacher}"})
            r.raise_for_status()
            print(f"{teacher} {class_id} {day}: {r.json()['share_id']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "https://localhost:8443")
