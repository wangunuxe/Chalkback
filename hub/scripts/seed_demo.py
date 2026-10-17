"""Load the demo data into a running Hub (for TD6 rehearsal and screenshots). Usually run through `make mock`.

    python hub/scripts/seed_demo.py [https://localhost:8443]

The Hub starts empty; this is the only place demo data comes from. As department head H1 it uploads and approves the
French syllabus (contracts/examples/syllabus.json, approved first, so it is the school's main syllabus) and a maths syllabus.

Goes through the real POST /api/coverage (same path as C's console upload), using mock tokens:
- T1 -> 4A: normal progress (same identity as the console's mock teacher T1)
- T2 -> 4B: only 1 knowledge point covered since the start of term -> triggers "won't finish before the exam"
- T2 -> 4C: covered KP02, so T1's teacher view shows "another class covered it, you haven't yet"
French knowledge points follow contracts/examples/syllabus.json (KP01-KP04). Update together once the demo syllabus (H4) is finalized.
Maths is taught by T3 to 4A and 4B, so classes have several courses.
Courses: 5 courses in 3 classes; T1, T2 and T3 each sent one summary (demo text standing in for the screenpipe summary).
Running the script again does not duplicate anything: lessons replace themselves, existing syllabi and courses are skipped.
"""
import json
import sys
from pathlib import Path

import httpx

HEAD = {"Authorization": "Bearer mock-token-H1"}
FRENCH_SYLLABUS = json.loads((Path(__file__).resolve().parents[2] / "contracts" / "examples" / "syllabus.json").read_text(encoding="utf-8"))
FRENCH = FRENCH_SYLLABUS["syllabus_id"]
MATHS = {
    "syllabus_id": "maths-4e", "version": 1, "status": "draft", "subject": "mathématiques", "level": "4e",
    "knowledge_points": [
        {"kp_id": "M01", "title": "Les fractions", "keywords": ["fraction", "numérateur", "dénominateur"]},
        {"kp_id": "M02", "title": "Le théorème de Pythagore", "keywords": ["Pythagore", "hypoténuse", "triangle rectangle"]},
        {"kp_id": "M03", "title": "Les équations du premier degré", "keywords": ["équation", "inconnue"]},
        {"kp_id": "M04", "title": "Le calcul littéral", "keywords": ["développer", "factoriser"]},
    ],
}

LESSONS = [
    ("T1", "4A", FRENCH, "2026-09-14", {"KP01": 6.0}),
    ("T1", "4A", FRENCH, "2026-10-17", {"KP03": 4.5}),
    ("T2", "4B", FRENCH, "2026-09-01", {"KP01": 5.0}),
    ("T2", "4C", FRENCH, "2026-09-03", {"KP01": 4.0}),
    ("T2", "4C", FRENCH, "2026-09-24", {"KP02": 7.5}),
    ("T2", "4C", FRENCH, "2026-10-15", {"KP04": 3.0}),
    ("T3", "4A", "maths-4e", "2026-09-15", {"M01": 8.0}),
    ("T3", "4A", "maths-4e", "2026-10-06", {"M02": 10.0}),
    ("T3", "4B", "maths-4e", "2026-09-16", {"M01": 7.0}),
]

# (teacher, name, class, syllabus, description, summary sent to the department head or None)
COURSES = [
    ("T1", "Grammaire — 4A", "4A", FRENCH, "Les temps du passé, trimestre 1",
     "Grammaire — 4A, class 4A: 2 lessons recorded between 14 September and 17 October.\n"
     "Taught so far (10.5 min in total): Le passé composé avec avoir (6 min), L'accord du participe passé (4.5 min).\n"
     "Still to teach: Le passé composé avec être, L'imparfait.\n"
     "Several students still forget the agreement with a COD placed before the verb; a short review is planned next lesson.\n"
     "Next: Le passé composé avec être."),
    ("T2", "Grammaire — 4B", "4B", FRENCH, "", None),
    ("T2", "Soutien grammaire — 4C", "4C", FRENCH, "Groupe de soutien du jeudi",
     "Soutien grammaire — 4C, class 4C: 3 lessons recorded between 3 September and 15 October.\n"
     "Taught so far (14.5 min in total): Le passé composé avec avoir (4 min), Le passé composé avec être (7.5 min), L'imparfait (3 min).\n"
     "Still to teach: L'accord du participe passé.\n"
     "The group is more confident with être verbs after the extra exercises.\n"
     "Next: L'accord du participe passé."),
    ("T3", "Mathématiques — 4A", "4A", "maths-4e", "Nombres et géométrie",
     "Mathématiques — 4A, class 4A: 2 lessons recorded between 15 September and 6 October.\n"
     "Taught so far (18 min in total): Les fractions (8 min), Le théorème de Pythagore (10 min).\n"
     "Still to teach: Les équations du premier degré, Le calcul littéral.\n"
     "Most students apply Pythagoras correctly; identifying the hypotenuse still needs practice.\n"
     "Next: Les équations du premier degré."),
    ("T3", "Mathématiques — 4B", "4B", "maths-4e", "", None),
]


def auth(teacher: str) -> dict:
    return {"Authorization": f"Bearer mock-token-{teacher}"}


def seed_syllabi(client) -> None:
    """French first: the syllabus approved first is the school's main one (board, matrix, forecast)."""
    for syllabus in (FRENCH_SYLLABUS, MATHS):
        sid = syllabus["syllabus_id"]
        if any(s["syllabus_id"] == sid for s in client.get("/api/syllabus", headers=HEAD).json()):
            print(f"syllabus {sid}: already approved")
            continue
        client.post("/api/syllabus", json={**syllabus, "status": "draft"}, headers=HEAD).raise_for_status()
        client.post(f"/api/syllabus/{sid}/approve", headers=HEAD).raise_for_status()
        print(f"syllabus {sid}: uploaded and approved by H1")


def seed_lessons(client) -> None:
    syllabi = {s["syllabus_id"]: s for s in client.get("/api/syllabus", headers=HEAD).json()}
    for teacher, class_id, syllabus_id, day, minutes in LESSONS:
        syllabus = syllabi[syllabus_id]
        body = {
            "lesson_id": f"L-{teacher}-{day.replace('-', '')}-1000",
            "class_id": class_id,
            "date": day,
            "syllabus_id": syllabus_id,
            "syllabus_version": syllabus["version"],
            "points": [{"kp_id": kp["kp_id"], "covered": kp["kp_id"] in minutes,
                        "minutes": minutes.get(kp["kp_id"], 0)} for kp in syllabus["knowledge_points"]],
        }
        r = client.post("/api/coverage", json=body, headers=auth(teacher))
        r.raise_for_status()
        print(f"{teacher} {class_id} {day}: {r.json()['share_id']}")


def seed_courses(client) -> None:
    for teacher, name, class_id, syllabus_id, description, summary in COURSES:
        existing = [c for c in client.get("/api/courses", headers=auth(teacher)).json()
                    if c["class_id"] == class_id and c["syllabus"]["syllabus_id"] == syllabus_id]
        if existing:
            print(f"{teacher} course {name!r}: already there")
            continue
        r = client.post("/api/courses", headers=auth(teacher), json={
            "name": name, "class_id": class_id, "syllabus_id": syllabus_id, "description": description})
        r.raise_for_status()
        course_id = r.json()["course_id"]
        if summary:
            client.put(f"/api/courses/{course_id}/summary", headers=auth(teacher), json={"text": summary}).raise_for_status()
        print(f"{teacher} course {name!r}: {course_id}{' (summary sent)' if summary else ''}")


def main(hub: str) -> None:
    with httpx.Client(base_url=hub, verify=False) as client:  # the local Hub uses a self-signed certificate
        seed_syllabi(client)
        seed_lessons(client)
        seed_courses(client)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "https://localhost:8443")
