<!-- Owner: D (TD7). For school admins and department heads. Teachers' setup is in SETUP.md. -->

# ChalkBack Hub — guide for school admins and department heads

The **Hub** is the only part of ChalkBack shared by the whole school. Each teacher's laptop records the lesson,
generates quizzes and spots syllabus gaps on its own. After the teacher approves it, the laptop sends the Hub one thing:
**which syllabus points a class covered, and for how many minutes.** The Hub combines these into a syllabus
progress board for the school.

## What the Hub stores, and what it never sees

| The Hub stores | The Hub never receives |
| --- | --- |
| Workspace, invite codes, members (name, role, token) | Audio, transcripts, screenshots |
| Syllabus versions (drafts and approved) | Lesson text, quiz questions, student answers |
| Per lesson: class, date, syllabus point, covered yes/no, minutes | screenpipe IDs, segment IDs, timestamps |
| Audit log: who did what, and when | The content of anything that was approved |

This boundary is checked twice: once on the teacher's laptop before upload, and again at the Hub. The Hub rejects
any upload that has even one field more than the `coverage_share` format (for example a `transcript` or a `quote`)
with `422`, and stores nothing from it.

---

## 1. Run the Hub

### On one computer (demo, pilot)

Requires Docker. From the repository root:

```bash
make up            # starts the Hub and a teacher console
```

- Hub: **<https://localhost:8443>** (API reference at `/docs`). The certificate is self-signed, so the
  browser warns once. Choose *Advanced → Continue*.
- Stop with `make down`. Data is kept in the `hub-data` Docker volume.
- `docker compose down -v` deletes all Hub data. Do this after upgrading if the Hub fails to start.
- `make up` runs the Hub in **test mode** (`HUB_MOCK_AUTH=1`): the public `DEMO-*` invite codes and
  `mock-token-<id>` tokens work. Use it only on your own computer.

Without Docker: `pip install -r hub/requirements.txt && make hub` (<https://localhost:8000>, also in test mode).

### For a whole school

`hub/Dockerfile` builds a standard container image. Run it on any container host and keep `/data` on a persistent
volume. Every teacher laptop must be able to reach the Hub's address.

The image starts in **production mode**: test tokens are refused and the `DEMO-*` codes do not work (they are
published in this repository, so anyone could use them to join as admin). Set your own codes with `HUB_INVITES`
before anyone joins. The built-in certificate is self-signed for `localhost`; on a public address, put the Hub
behind a proxy or host that provides a real certificate.

| Setting | Default | Meaning |
| --- | --- | --- |
| `HUB_DB` | `/data/chalkback.db` | SQLite database file |
| `HUB_EXAM_DATE` | `2026-12-18` | Exam date used for the "won't finish before the exam" alert (`YYYY-MM-DD`) |
| `HUB_INVITES` | — | Your school's invite codes: `teacher=CODE,head=CODE,admin=CODE`. Pick long, unguessable codes. Without it, nobody can join in production mode. |
| `HUB_MOCK_AUTH` | off | `1` = test mode: accepts `mock-token-<id>` tokens and the `DEMO-*` codes. **Never set it on a public address.** |

## 2. Workspace and invite codes (school admin)

On first start the Hub creates the workspace `W1` with **one invite code per role**, taken from `HUB_INVITES`:

| Invite code | Give it to | Role |
| --- | --- | --- |
| your `teacher=` code | every teacher | teacher |
| your `head=` code | department heads | head |
| your `admin=` code | yourself | admin |

In test mode (`make up`, `make hub`) the codes are `DEMO-TEACHER`, `DEMO-HEAD` and `DEMO-ADMIN`.

- A code only works for its own role. Choosing *School admin* with the teacher code is refused (`403`), so a
  teacher cannot make themselves an admin.
- Teachers enter the code in the console setup wizard (`/setup`, see SETUP.md).
  Heads and admins enter it on the Hub's home page.
- Each join creates a member and a personal token, and writes a `join` entry in the audit log.
- As admin, the dashboard shows the invite codes and how many teachers, heads and admins have joined.

## 3. Publish the syllabus (department head, approval A4)

Teachers' laptops always use the **latest approved** syllabus. A draft has no effect until a head approves it.

On the dashboard, as *Department head* → **Syllabus** panel:

1. **Upload a new draft.** The editor starts with the current version as JSON. Change the knowledge points and
   upload. The Hub checks the format and assigns the next version number itself.
2. The draft appears under the panel. Teachers still get the previous version.
3. **Approve vN.** This version now applies to everyone. The audit log records `approve_syllabus`
   with the target `<syllabus_id>@v<N>`.

Same steps with the API:

```bash
curl -k -X POST https://localhost:8443/api/syllabus -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" -d @syllabus.json
curl -k -X POST https://localhost:8443/api/syllabus/fr-grammaire-4e/approve -H "Authorization: Bearer $TOKEN"
```

## 4. What each role sees

Open the Hub home page, sign in, then switch roles with the buttons at the top of the dashboard. The page
refreshes every 3 seconds.

| | Teacher | Department head | School admin |
| --- | --- | --- | --- |
| Class syllabus progress | Own classes, per knowledge point | All classes, knowledge point × class matrix | All classes, totals only |
| "Covered elsewhere, not yet in your class" | Yes, without naming the other class | No | No |
| Exam alert | Own classes | All classes | All classes |
| Syllabus | Read | Upload drafts and approve | Read |
| Invite codes and members | — | — | Yes |
| Audit log | Own actions | Whole school | Whole school |
| Recordings, transcripts, quizzes, student answers | Only on their own laptop | Never | Never |

A teacher "owns" a class once they have shared coverage for it.

## 5. Sharing and withdrawing coverage (approvals A3, A5)

- After a lesson, the teacher reviews it in the console (`/review`) and clicks approve. Only then does the
  laptop send the coverage. The audit log records `share_coverage`.
- If the same lesson is shared again, the new version replaces the old one, so minutes are never counted twice.
- The Hub refuses (`422`) a share for another teacher's lesson, for a syllabus version that was never approved,
  or with knowledge points that are not in that version.
- The teacher can withdraw a share at any time in the console (`/shares`). The Hub deletes it, the dashboard
  updates within 3 seconds, and the audit log records `revoke`. Only the teacher who shared it can withdraw it.

## 6. Exam alert

For each class:

```
at risk  ⇔  uncovered points  >  weeks until the exam  ×  points covered per week so far
```

"Points covered per week" = covered points ÷ weeks since the class's first shared lesson (at least 1 week).
Set the exam date with `HUB_EXAM_DATE`.

## 7. Audit log

The Hub logs every join, approval and withdrawal: `join`, `share_coverage`, `revoke`, `approve_syllabus`.
Each entry has who (role and id), the action, the target id and the
time. **It never contains the content itself.** Read it on the dashboard or with `GET /api/audit`.

## 8. API reference

All requests except `join` need `Authorization: Bearer <token>`.

| Method | Path | Who | Purpose |
| --- | --- | --- | --- |
| POST | `/api/join` | anyone with a code | `{invite_code, display_name, role}` → `{teacher_id, token, workspace_id}` |
| GET | `/api/syllabus/current` | all | Latest approved syllabus |
| POST | `/api/syllabus` | head | Upload a draft → `{syllabus_id, version}` |
| POST | `/api/syllabus/{id}/approve` | head | Approve the latest draft |
| POST | `/api/coverage` | teacher | Share one lesson's coverage → `{share_id}` |
| DELETE | `/api/coverage/{share_id}` | that teacher | Withdraw a share |
| GET | `/api/coverage?class_id=` | by role | Covered / not covered per knowledge point, with minutes |
| GET | `/api/dashboard?view=teacher\|head\|admin` | matching role | Dashboard data and alerts |
| GET | `/api/audit` | all, filtered by role | Audit entries |

## 9. Rehearsal data

With the Hub running in test mode (`make up` or `make hub`; the script uses test tokens):

```bash
python hub/scripts/seed_demo.py            # default https://localhost:8443
```

This shares six example lessons through the real API: class 4A is on track, 4B triggers the exam alert, and
teacher T1 sees a point covered in another class but not in theirs. To see T1's view, choose *I already have a
token* on the home page and enter `mock-token-T1`.

## Known limits

- **Department heads currently see the whole school**, not only their grade, because the data formats don't yet
  map classes to grades. A demo with a single grade is not affected.
- There is no screen yet for creating more workspaces, rotating invite codes or changing the exam date. These come
  from the first start, `HUB_INVITES` and `HUB_EXAM_DATE`. To change a code, update `HUB_INVITES` and restart;
  the old code keeps working until it is removed from the database.
- Syllabus versions are numbered per syllabus, not per workspace, and the "current" syllabus is the newest
  approved one in the workspace. This is fine for one school and one subject.
