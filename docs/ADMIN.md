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
| Courses (teacher, class, syllabus) and the course summaries teachers chose to send | Anything a teacher did not send |
| Audit log: who did what, and when | The content of anything that was approved |

A syllabus file used for AI import (section 3) is not stored: the Hub reads it, sends it to the AI service and discards it.

This boundary is checked twice: once on the teacher's laptop before upload, and again at the Hub. The Hub rejects
any upload that has even one field more than the `coverage_share` format (for example a `transcript` or a `quote`)
with `422`, and stores nothing from it.

---

## 1. Run the Hub

### On one computer (demo, pilot)

Requires Docker. From the repository root:

```bash
make up            # starts the Hub and a teacher console, both empty
make mock          # optional: load the demo data (see section 9)
```

- Hub: **<https://localhost:8443>** (API reference at `/docs`). The certificate is self-signed, so the
  browser warns once. Choose *Advanced → Continue*.
- Stop with `make down`. Data is kept in the `hub-data` Docker volume.
- `make reset` (= `docker compose down -v`) deletes all Hub data. Do this after upgrading if the Hub fails to start.
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
| `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` | — | Turns on syllabus import with AI (section 3), with Claude or Gemini. Without either, heads add points by hand. Put it in `.env` at the repo root (`cp .env.example .env`); `.env` is never committed. |
| `HUB_AI_MODEL` | `claude-opus-5-5` / `gemini-flash-latest` | Model id for syllabus import |
| `HUB_AI_PROVIDER` | `anthropic` | `anthropic` or `gemini`, only needed when both keys are set |
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
A new Hub has no syllabus: the dashboard shows "No syllabus yet" until the head uploads and approves the first one.

On the dashboard, as *Department head* → **Syllabus** panel:

1. **Upload a new draft.** The editor starts with the current version as JSON. Change the knowledge points and
   upload. The Hub checks the format and assigns the next version number itself.
   **From a file:** choose the syllabus file (PDF, Word, PowerPoint, TXT or Markdown, up to 5 MB) and click
   **Summarise with AI**. The panel shows the knowledge point list the AI found. Points that match the current
   version keep their id (`KP01`…), so coverage already shared still counts; new points get the next numbers and are
   marked *new*. Next to each point the list shows the keywords the AI wrote for it (what the pipe searches lessons
   for); change them under **Edit points and keywords by hand**. If the file is for another subject (for example Chinese while the
   current syllabus is French), it becomes a separate syllabus for that subject (`chinois-college`) with its own
   numbering, or the next version of it if one exists; the current syllabus is not changed. The file is sent to the AI service (Anthropic or Google) and not
   stored by the Hub. Needs `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`.
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
| Class syllabus progress | Own courses: one table per course, its syllabus's knowledge points covered or not | One subject at a time (picker at the top): all its classes, knowledge point × class matrix | All classes, totals only |
| Classes and courses | Own courses | Every class → its courses → knowledge points covered | Every class → its courses, progress only |
| Course summaries | Review, send, withdraw their own | The ones teachers sent | No |
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

### Classes and courses (department head)

The department head looks at one subject at a time: choose it with the **Subject** picker at the top of the board
(shown once two syllabi are approved; the main syllabus is the default, and the choice is remembered on this computer).
The exam alert, "Classes and courses", the exam forecast, the coverage matrix and the syllabus editor then show only
that subject.

The "Classes and courses" card lists every class (a group of students) with the courses taught to it. A course is
one teacher teaching one syllabus to one class, e.g. *Grammaire — 4A* (French, T1) and *Mathématiques — 4A* (maths, T3).
- Each class shows its overall progress: knowledge points taught across all its courses.
- Open a course to see which knowledge points were covered (with minutes), how many lessons were shared,
  and the summary the teacher sent.
- A summary is written by screenpipe on the teacher's laptop. The teacher reads it, can edit it, and only then sends
  it; they can withdraw it at any time, and it disappears from your board within 3 seconds.

A new subject needs its own syllabus: upload and approve it like the first one; it then appears in the Subject picker.

## 6. Exam alert

For each class:

```
at risk  ⇔  uncovered points  >  weeks until the exam  ×  points covered per week so far
```

"Points covered per week" = covered points ÷ weeks since the class's first shared lesson (at least 1 week).
Set the exam date with `HUB_EXAM_DATE`.

## 7. Audit log

The Hub logs every join, approval and withdrawal: `join`, `share_coverage`, `revoke`, `approve_syllabus`, and `share_summary` / `withdraw_summary` when a teacher sends a course summary to the department head or withdraws it.
Each entry has who (role and id), the action, the target id and the
time. **It never contains the content itself.** Read it on the dashboard or with `GET /api/audit`.

## 8. API reference

All requests except `join` need `Authorization: Bearer <token>`.

| Method | Path | Who | Purpose |
| --- | --- | --- | --- |
| POST | `/api/join` | anyone with a code | `{invite_code, display_name, role}` → `{teacher_id, token, workspace_id}` |
| GET | `/api/syllabus/current` | all | Latest approved version of the main syllabus (`?syllabus_id=` for another) |
| GET | `/api/syllabus` | all | Latest approved version of every syllabus |
| GET | `/api/courses` | by role | Courses by class with progress (head: plus knowledge points and summaries) |
| POST | `/api/courses` | teacher | Create a course `{name, class_id, syllabus_id, description?}` |
| PUT / DELETE | `/api/courses/{id}/summary` | that teacher | Send or withdraw the course summary |
| POST | `/api/syllabus` | head | Upload a draft → `{syllabus_id, version}` |
| POST | `/api/syllabus/{id}/approve` | head | Approve the latest draft |
| POST | `/api/syllabus/extract` | head | AI suggestion from a file `{filename, content_base64}` → `{syllabus, kept, new, dropped}`; saves nothing |
| POST | `/api/coverage` | teacher | Share one lesson's coverage → `{share_id}` |
| DELETE | `/api/coverage/{share_id}` | that teacher | Withdraw a share |
| GET | `/api/coverage?class_id=` | by role | Covered / not covered per knowledge point, with minutes |
| GET | `/api/dashboard?view=teacher\|head\|admin` | matching role | Dashboard data and alerts |
| GET | `/api/audit` | all, filtered by role | Audit entries |

## 9. Rehearsal data

The Hub starts with no data. With it running in test mode (the script uses test tokens):

```bash
make mock          # Docker (make up): Hub https://localhost:8443 and the console
make mock-local    # without Docker (make hub + make teacher): Hub https://localhost:8000
```

As department head H1 this approves the French syllabus (the main one) and a maths syllabus, shares nine example
lessons through the real API (class 4A is on track, 4B triggers the exam alert), and creates five courses, three with a summary. Running it again adds nothing new. To see T1's view, choose *I already have a
token* on the home page and enter `mock-token-T1`.

## Known limits

- **Department heads currently see the whole school**, not only their grade, because the data formats don't yet
  map classes to grades. A demo with a single grade is not affected.
- There is no screen yet for creating more workspaces, rotating invite codes or changing the exam date. These come
  from the first start, `HUB_INVITES` and `HUB_EXAM_DATE`. To change a code, update `HUB_INVITES` and restart;
  the old code keeps working until it is removed from the database.
- Syllabus versions are numbered per syllabus, not per workspace, and the "current" syllabus is the newest
  approved one in the workspace. This is fine for one school and one subject.
