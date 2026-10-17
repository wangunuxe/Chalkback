"""Load demo coverage data into a running Hub (for TD6 rehearsal and screenshots).

    python hub/scripts/seed_demo.py [https://localhost:8443]

Goes through the real POST /api/coverage (same path as C's console upload), using mock tokens:
- T1 -> 4A: normal progress (same identity as the console's mock teacher T1)
- T2 -> 4B: only 1 knowledge point covered since the start of term -> triggers "won't finish before the exam"
- T2 -> 4C: covered KP02, so T1's teacher view shows "another class covered it, you haven't yet"
Knowledge points follow contracts/examples/syllabus.json (KP01-KP04). Update together once the demo syllabus (H4) is finalized.
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
    with httpx.Client(base_url=hub, verify=False) as client:  # the local Hub uses a self-signed certificate
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
