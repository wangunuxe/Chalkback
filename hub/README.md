# hub/ — school Hub

Owner: D. In the cloud, publicly reachable (§6.4). Dashboard data comes only from approved uploads of `coverage_share`.

```bash
pip install -r requirements.txt
make hub                                         # from the repo root: https://localhost:8000 (test mode), API docs at /docs
pytest
```

All endpoints are real implementations; data is stored in SQLite (`HUB_DB`).

Dashboard (TD6): open the Hub home page and log in (invite code, or paste the token from the console's `config.json`), then go to `/dashboard.html`. Once all three roles have logged in, you can switch between them with one click at the top; the page refreshes every 3 seconds, so the dashboard updates automatically after a teacher withdraws. The page loads no external resources.
- Teacher: only their own classes — whether each knowledge point was covered and for how many minutes, plus knowledge points that "another class has covered but you haven't" (without naming the class).
- Department head: knowledge point × class matrix, syllabus panel (upload draft, approve), list of drafts awaiting approval.
- Admin: per-class progress summary (no knowledge point detail), invite codes, head count per role.
- All three roles can see the audit log, filtered by role.
- Warning: `remaining uncovered knowledge points > weeks left until the exam × average coverage per week`. Average coverage per week = covered count ÷ weeks from the class's first uploaded lesson to today (at least 1 week). The exam date defaults to `2026-12-18`; override it with the env var `HUB_EXAM_DATE=YYYY-MM-DD`.

Rehearsal data: with the Hub running, run `python hub/scripts/seed_demo.py [Hub URL]` (default `https://localhost:8443`, the `make up` address; pass `https://localhost:8000` when running with `make hub`; the script uses a mock token, so it only works in test mode). It uploads sample coverage data for 3 classes through the real API (4A on track, 4B triggers the warning, T1 shows the same-grade comparison).

Coverage table (TD4, TD5, approvals A3, A5):
- `POST /api/coverage` (teacher): strictly validated against the `coverage_share` schema; even one extra field returns 422 (privacy boundary). If the same teacher re-uploads the same lesson, the new one replaces the old. Writes audit `share_coverage`.
- `DELETE /api/coverage/{share_id}`: only the uploader can withdraw (others get 403, nonexistent 404); writes audit `revoke`.
- `GET /api/coverage?class_id=`: lists each knowledge point of the currently approved syllabus and aggregates all uploads for that class (`covered` means "covered in any lesson", `minutes` are summed). Teachers can only query classes they have uploaded for.
- `GET /api/audit`: teachers see their own records; department heads and admins see the whole school's.

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
| `app/routes/dashboard.py` | Three role views + pre-exam warning | TD6 |
| `app/routes/audit.py` | Audit log | TD5, TD6 |
| `app/db.py` | SQLite tables | TD2–TD5 |
| `app/auth.py` | token → role | TD2 |
| `app/static/` | Dashboard frontend | TD6 |

## TBD

- Filtering the department head's view to "their grade" needs a class → grade mapping, which the contracts don't have yet (§4 table). **For now department heads see the whole school** (coverage table and audit log); the demo has only one grade, so the result is the same.
- The exam date lives in workspace settings; the settings API is not defined.
