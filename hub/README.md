# hub/ — school Hub

Owner: D. In the cloud, publicly reachable (§6.4). Dashboard data comes only from approved uploads of `coverage_share`.

```bash
pip install -r requirements.txt
make hub                                         # from the repo root: https://localhost:8000 (test mode), API docs at /docs
pytest
```

All endpoints are real implementations; data is stored in SQLite (`HUB_DB`).

Dashboard (TD6): open the Hub home page and log in (invite code, or paste the token from the console's `config.json`), then go to `/dashboard.html`. Once all three roles have logged in, you can switch between them with one click at the top; the page refreshes every 3 seconds, so the dashboard updates automatically after a teacher withdraws. The page loads no external resources.
- Teacher: only their own classes — whether each knowledge point was covered and for how many minutes, plus knowledge points that "another class has covered but you haven't" (without naming the class). "My courses": create a course per class and syllabus, get its summary from screenpipe, review it and send it to the department head, or withdraw it.
- Department head: "Classes and courses" hierarchy (each class → its courses → knowledge points covered, and the summary the teacher sent), knowledge point × class matrix, syllabus panel (upload draft, approve), list of drafts awaiting approval.
- Admin: per-class progress summary (no knowledge point detail), classes and courses with progress only (no knowledge points, no summaries), invite codes, head count per role.
- All three roles can see the audit log, filtered by role.
- Warning: `remaining uncovered knowledge points > weeks left until the exam × average coverage per week`. Average coverage per week = covered count ÷ weeks from the class's first uploaded lesson to today (at least 1 week). The exam date defaults to `2026-12-18`; override it with the env var `HUB_EXAM_DATE=YYYY-MM-DD`.

Rehearsal data: with the Hub running, run `python hub/scripts/seed_demo.py [Hub URL]` (default `https://localhost:8443`, the `make up` address; pass `https://localhost:8000` when running with `make hub`; the script uses a mock token, so it only works in test mode). It uploads sample coverage data for 3 classes through the real API (4A on track, 4B triggers the warning, T1 shows the same-grade comparison), plus a maths syllabus (approved by H1) with lessons by T3 in 4A and 4B, and 5 courses in 3 classes, 3 of them with a summary sent. Running it again does not duplicate anything.

Coverage table (TD4, TD5, approvals A3, A5):
- `POST /api/coverage` (teacher): strictly validated against the `coverage_share` schema; even one extra field returns 422 (privacy boundary). If the same teacher re-uploads the same lesson, the new one replaces the old. Writes audit `share_coverage`.
- `DELETE /api/coverage/{share_id}`: only the uploader can withdraw (others get 403, nonexistent 404); writes audit `revoke`.
- `GET /api/coverage?class_id=`: lists each knowledge point of the currently approved syllabus and aggregates all uploads for that class (`covered` means "covered in any lesson", `minutes` are summed). Teachers can only query classes they have uploaded for.
- `GET /api/audit`: teachers see their own records; department heads and admins see the whole school's.

Courses: a course is what one teacher teaches to one class (a group of students) from one syllabus; at most one per teacher, class and syllabus, so every shared lesson belongs to exactly one course. Its progress comes from that teacher's coverage shares for the class and syllabus.
- `GET /api/courses`: teachers get their own courses; department heads get every course with its knowledge points (`points`: covered, minutes, title) and the summary if one was sent; admins get every course with progress only (no `points`, no `summary`). Each course also has its teacher (`id`, display name), syllabus, and `lessons` (`count`, `first`, `last` date).
- `POST /api/courses` (teacher) `{name, class_id, syllabus_id, description?}`: the syllabus must have an approved version; a second course for the same class and syllabus returns 409.
- `PUT /api/courses/{id}/summary` (owner) `{text}`: sends the summary to the department head, or replaces the one sent before (1–3000 characters). Writes audit `share_summary`. `DELETE /api/courses/{id}/summary` withdraws it and writes `withdraw_summary`.
- `DELETE /api/courses/{id}` (owner): only while no summary is sent (withdraw it first, otherwise 409).
- The summary text is written by the screenpipe pipe on the teacher's computer. **For now it is mocked** in `app/static/screenpipe_summary.js` (built from the course's coverage); replace that one function when the real summary is ready. The teacher always reviews it, and can edit it, before sending.
- `GET /api/syllabus`: latest approved version of every syllabus, used to pick one for a new course. `GET /api/syllabus/current` returns the school's main syllabus (the one approved first), or another one with `?syllabus_id=`; approving a syllabus for another subject does not change the main one. The dashboard's matrix, forecast and per-class board use the main syllabus; other subjects appear per course.

Syllabus (TD3, approval A4): the department head uploads with `POST /api/syllabus`; the Hub validates the format and stores it as a draft, with the version number auto-incremented (any `version` or `status` from the uploader is ignored). The department head approves the latest draft with `POST /api/syllabus/{id}/approve`, which writes audit `approve_syllabus`. `GET /api/syllabus/current` returns only the latest approved version; drafts don't take effect. On startup the Hub preloads `contracts/examples/syllabus.json` as approved v1.

Joining (TD2): on startup the Hub creates the demo workspace `W1` and three invite codes, one per role; a code used with the wrong role is rejected:

| Invite code | Role |
| --- | --- |
| `DEMO-TEACHER` | teacher |
| `DEMO-HEAD` | head |
| `DEMO-ADMIN` | admin |

Put the token returned by `POST /api/join` in `Authorization: Bearer <token>`.
Only **test mode** (`HUB_MOCK_AUTH=1`, already set by `make hub` and `docker-compose.yml`) accepts mock auth `Authorization: Bearer mock-token-<id>` (ids starting with `H` are department heads, `ADM` are admins, all others are teachers) and the `DEMO-*` invite codes above. The default is production mode (not set in `hub/Dockerfile`): mock tokens always get 401, `DEMO-*` codes are disabled, and the school's invite codes are set with `HUB_INVITES="teacher=code,head=code,admin=code"`.

Upload checks (TD4): besides the schema, `POST /api/coverage` requires that the teacher in `lesson_id` is the uploader, the syllabus version is approved, and the knowledge points are in that version; otherwise 422.

| File | Contents | Task |
| --- | --- | --- |
| `app/routes/join.py` | Invite code join, token | TD2 |
| `app/routes/syllabus.py` | Syllabus drafts, approval (A4), versions | TD3 |
| `app/routes/coverage.py` | Receive / withdraw coverage_share (A3, A5), coverage table | TD4, TD5 |
| `app/routes/courses.py` | Courses, course summaries sent to the department head | — |
| `app/routes/dashboard.py` | Three role views + pre-exam warning | TD6 |
| `app/routes/audit.py` | Audit log | TD5, TD6 |
| `app/db.py` | SQLite tables | TD2–TD5 |
| `app/auth.py` | token → role | TD2 |
| `app/static/` | Dashboard frontend | TD6 |

## TBD

- Filtering the department head's view to "their grade" needs a class → grade mapping, which the contracts don't have yet (§4 table). **For now department heads see the whole school** (coverage table and audit log); the demo has only one grade, so the result is the same.
- The exam date lives in workspace settings; the settings API is not defined.
