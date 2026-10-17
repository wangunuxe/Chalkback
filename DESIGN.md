# ChalkBack design doc

Oct 17, 2026 · @Aurora

ChalkBack is a teaching assistant for schools. screenpipe remembers the lesson on each teacher's computer; after class, the ChalkBack pipe automatically generates a quiz and student game, missed-point alerts and learning stats. After the teacher's approval, only syllabus coverage data goes to the school Hub, where it feeds the knowledge point coverage table and the syllabus progress dashboard. This project is entered in the screenpipe hackathon **Track 3: make it work for teams**; submission deadline is Oct 18, 19:00.

## 0. Rules for AI collaborators

If you are an AI helping a team member write code, read this section first, then the parts of §5–§9 relevant to your role.

- **Confirm the role first**: you serve only one of roles A, B, C, D (see §8). Only write code in the directories that role owns (see §7).
- **Data contracts are hard constraints**: the JSON formats in §5 and the interfaces in §6 must not be changed unilaterally. If a change is needed, propose it first; once all four team members agree, update `contracts/` and this document at the same time.
- **Start with mocks**: if upstream isn't done, use the sample data in `contracts/examples/`; don't wait.
- **Privacy is a hard constraint**: audio recordings, screenshots, raw transcripts and screenpipe ids never leave the teacher's computer. Data uploaded to the Hub may only be the fields marked "shareable" in §5.
- **Conventions**: all times are ISO 8601 with time zone (`Europe/Paris`, e.g. `2026-10-17T10:12:05+02:00`); code, field names and file names are in English; UI text is in French or English (TBD by the team); lesson content language follows the actual demo lesson.
- **When unsure, ask**: for anything this document doesn't make clear, ask the relevant team member first; don't invent new data formats or interfaces.
- **Definition of done**: meets the acceptance criteria for the task in §8, and runs end to end with the data in `contracts/examples/`.

## 1. Track 3 requirements and how ChalkBack maps to them

Track 3 original text: turn a personal workflow into automation others can use, with configuration, approval and sharing tools; you need to show a workflow others can use, including setup instructions and approval steps.

| What judges look for | ChalkBack's implementation | Evidence (shown in the demo or Q&A) |
| --- | --- | --- |
| Others can use it | A new teacher joins the school workspace with an invite code, installs the pipe with one command, and the setup wizard does the rest | Timed result of someone outside the team installing by following `SETUP.md` |
| Setup instructions | `docs/SETUP.md`: install screenpipe → install pipe → open the console wizard → done | The document itself + newcomer test |
| Approval steps | 5 approval points: informed consent at install, review questions before publishing, approve coverage data before sharing, head approves syllabus version, teacher can withdraw at any time | Review page, audit log, withdraw action |
| Sharing tools | Shared syllabus, shared pipe, knowledge point coverage table, syllabus progress dashboard | Hub pages |
| Roles and permissions | Three views: teacher, department head, school admin; pipe has read-only permissions | Switching roles on the dashboard |
| Trust and privacy | Raw data never leaves the teacher's computer; only approved coverage data is uploaded | The boundary in the architecture diagram |

Personal-level learning (the agent learns the teacher's style from their past question-writing screens and review edits) is kept as the basis for Track 2; it also shows that "everyone shares the same pipe, but each teacher gets their own style".

## 2. System architecture

The system has two zones with only one gate between them: the teacher console. All data going from the teacher's computer to the school Hub must be approved by the teacher in the console.

&#91;embedded content: ChalkBack architecture · the two approval and trust components are highlighted\]

| Component | Runs on | Responsibility | Owner | Suggested tech |
| --- | --- | --- | --- | --- |
| screenpipe | Teacher's computer | Records the teacher's microphone transcription and screen text; used as is, unmodified | A deploys | screenpipe desktop (Windows or macOS) |
| chalkback-pipe | Teacher's computer, launched by screenpipe | After class: reconstructs the lesson, maps to knowledge points, generates questions and the student game, missed-point alerts, learns style; writes results to the outbox | A data part, B intelligence part | `pipe.md` + Python scripts, only calls the screenpipe local API |
| outbox | Teacher's computer `~/.chalkback/outbox/` | File interface between the pipe and the console | B writes, C reads | JSON files |
| Teacher console | Teacher's computer `https://localhost:4000` | Setup wizard, question review, serving the student game page locally and recording answers, share approval, share history and withdraw, sync with Hub | C | FastAPI + simple frontend |
| School Hub | Cloud (publicly reachable, HTTPS) | Workspaces and invite codes, shared syllabus, knowledge point coverage table (receives approved coverage data), role dashboards, audit log | D | FastAPI + SQLite + simple frontend |

The tech stack is a suggestion and can change, but the whole team must settle it before hour 3 and stay consistent.

### Agent: ChalkBack's "brain"

ChalkBack has only one agent: the AI agent running on the teacher's computer. When screenpipe launches chalkback-pipe according to the timetable, it runs a coding agent (pi by default, or claude-code), with the model chosen in screenpipe's AI preset. The console and Hub are ordinary software with no agent. The Hub makes one LLM call, outside the pipe: syllabus import (§6.4), where the model only suggests knowledge points from a file the head uploads; the head edits the suggestion and it goes through the normal draft and approval A4.

- **Instructions**: `pipe/pipe.md` (the 8 steps in §6.1) and the four prompts under `pipe/prompts/`.
- **Memory**: screenpipe local data (read-only), the style profile, past coverage tables.
- **Tools**: screenpipe `/search`, scripts under `pipe/scripts/`, writing to the outbox, sending notifications.
- **Boundary**: read-only access to screenpipe; uploads nothing directly; all output goes to the outbox first and waits for teacher approval.

The agent handles the parts that need judgment; fixed logic (fetching data, assembling segments, validating formats) goes to scripts:

| Agent judgment | Based on | Output |
| --- | --- | --- |
| Which knowledge point each explanation belongs to | Segments + syllabus | `coverage` |
| Whether to look back for points not covered today, and whether they were covered before | Lesson plan + past 21 days of records | `alerts` |
| What habits this teacher has when writing questions | Past question-writing screens + review edits | `style_profile` |
| Which questions to write, how many per knowledge point, how to phrase them | Coverage time + weights + style | `quiz` (each question with a source) + student game page game.html |

Why this matters for Track 3: the same agent (the same pipe) is distributed to the whole school, and each teacher's agent learns that teacher's own style; the agent's power is boxed in by read-only permissions and teacher approval, which is what makes a school willing to deploy it.

## 3. End-to-end workflow

Split into a one-time onboarding flow and a per-lesson loop. Steps marked **\[approval Ax\]** require a human sign-off; see §4.

**One-time: school and new teachers join**

1. The school admin creates a workspace in the Hub and generates an invite code.
2. The department head uploads the syllabus knowledge point list and publishes it as an official version **\[approval A4\]**.
3. The new teacher follows `docs/SETUP.md`: install screenpipe → install chalkback-pipe with one command → start the local console.
4. Console setup wizard: enter invite code → choose subject and class → fill in timetable → review and agree to "what is recorded, what is uploaded" **\[approval A1\]**. The wizard writes schedule rules into the pipe based on the timetable.

**Per-lesson loop**

1. **Class**: the teacher teaches as usual; screenpipe records microphone transcription and screen text.
2. **Auto-run after class**: screenpipe launches chalkback-pipe according to the timetable (read-only permissions).
3. **Reconstruct the lesson**: fetch the transcription and slide text for this lesson's time window and align them by timestamp into segments.
4. **Map to knowledge points**: generate this lesson's coverage table, storing only screenpipe timestamps and ids.
5. **Generate results**: missed-point alerts (confirmed by looking back over the past 21 days), quiz with sources and student game (weighted by teacher style and learning stats), weak points from Kahoot reports. Everything is written to the outbox and the teacher is notified.
6. **Teacher reviews questions** **\[approval A2\]**: approve, edit or reject. Edit records are fed back to the pipe to update the style profile.
7. **Publish the game**: the console serves the agent-generated student game page locally (`localhost`); the teacher opens it in the browser on their own computer.
8. **Students answer**: students open the game page on the teacher's computer, enter a nickname and answer; the console records answers and timing locally. No mobile version, not exposed to the campus network.
9. **Learning stats feedback**: the console aggregates answers by knowledge point and generates the weights file used for the next quiz.
10. **Teacher approves sharing coverage data** **\[approval A3\]**: only knowledge point, whether covered, and duration are uploaded.
11. **Dashboard update**: the Hub updates syllabus progress and warnings and writes to the audit log.
12. **Withdraw at any time** **\[approval A5\]**: the teacher withdraws any upload in the console; the Hub deletes it and records the action.

In addition, the teacher can query their own lesson records at any time in Claude via the screenpipe MCP (local only, not through the Hub).

## 4. Approvals, roles and configuration

**Five approval points** (each approval writes one `audit_event`; see §5)

| ID | What is approved | Who approves | Where | Result if not approved | Implemented by |
| --- | --- | --- | --- | --- | --- |
| A1 | Informed consent at install: recording scope, uploaded content, pipe permissions | Teacher | Console setup wizard | Installation cannot complete | C |
| A2 | Review of questions before publishing | Teacher | Console review page | Questions are not published | C |
| A3 | Approval before uploading coverage data | Teacher | Console review page | Data stays on the local machine | C |
| A4 | Syllabus version release | Department head | Hub syllabus page | New version doesn't take effect; old one stays in use | D |
| A5 | Withdraw uploaded data | Teacher | Console share history page | — | C initiates, D performs deletion |

**Roles and permissions**

| Content | Teacher | Department head | School admin |
| --- | --- | --- | --- |
| Own audio, screenshots, transcripts | Local only | Not visible | Not visible |
| Own questions and learning stats | Visible | Not visible (only on the teacher's machine) | Not visible |
| Class syllabus progress | Own classes | All classes in the grade | All classes in the school |
| Missed points compared with the same grade | Only to the teacher themself | No individual comparison visible | Not visible |
| Shared syllabus | Read-only | Edit and publish | Read-only |
| Workspace and invite codes | — | — | Manage |
| Audit log | Own records | Records for the grade | All records (not the content itself) |

**Shared configuration vs personal configuration**

| Configuration | Scope | Stored where |
| --- | --- | --- |
| chalkback-pipe itself (`pipe.md`, scripts, prompts, permission rules) | Shared school-wide, same version | GitHub repo `pipe/` |
| Syllabus knowledge point list | Shared school-wide, versioned | Hub |
| Workspace, class list | Shared school-wide | Hub |
| Timetable, lesson plans, auto-share toggle | Personal | `~/.chalkback/config.json`, `~/.chalkback/lesson_plans/` |
| Question style profile | Personal, never uploaded | `~/.chalkback/state/style_profile.json` |
| LLM API key | Personal or school-wide | screenpipe AI preset (not written to the code repo) |

## 5. Data contracts

All JSON. Each format has a JSON Schema in `contracts/` and a working sample file in `contracts/examples/`, finalized by everyone before hour 3. The sample content below (French grammar, class 4A) is only a placeholder; the actual topic is TBD.

| Contract | Producer → consumer | Location | Can it leave the teacher's computer |
| --- | --- | --- | --- |
| `syllabus` | D → A, B, C | Hub; local cache `~/.chalkback/cache/syllabus.json` | Already lives in the Hub |
| `lesson_plan` | C (filled in by teacher) → B | `~/.chalkback/lesson_plans/{class_id}/{date}.json` | No |
| `segment` | A → B | outbox `segments.json` | No |
| `coverage` | A → B, C | outbox `coverage.json` | Only as `coverage_share` |
| `quiz` | B → C | outbox `quiz.json` + student game page `game.html` | No (game is generated and served only locally) |
| `alerts` | B → C | outbox `alerts.json` | No |
| `style_profile` | B → B | `~/.chalkback/state/style_profile.json` | No |
| `edit_event` | C → B | `~/.chalkback/state/edits.jsonl` | No |
| `weights` | C → B | `~/.chalkback/state/weights.json` | No |
| `attempt` | Student game → C | Local `~/.chalkback/state/attempts.jsonl` | No |
| `kp_stats` | C (local stats) → C | Local | No |
| `audit_event` | D | Hub | Already lives in the Hub |

**syllabus**

```json
{"syllabus_id": "fr-grammaire-4e", "version": 1, "status": "approved", "subject": "français", "level": "4e",
 "knowledge_points": [{"kp_id": "KP01", "title": "Le passé composé avec avoir", "keywords": ["passé composé", "avoir"]}]}
```

**lesson\_plan**

```json
{"class_id": "4A", "date": "2026-10-17", "syllabus_id": "fr-grammaire-4e", "kp_ids": ["KP01", "KP02", "KP03"]}
```

**segment** (`lesson_id` format: `L-{teacher_id}-{YYYYMMDD}-{HHMM}`)

```json
{"segment_id": "S-L-T1-20261017-1000-003", "lesson_id": "L-T1-20261017-1000",
 "start": "2026-10-17T10:12:05+02:00", "end": "2026-10-17T10:16:40+02:00",
 "speech": "…raw transcript…", "slide_text": "…slide text on screen at the time…", "app_name": "PowerPoint",
 "evidence": {"transcription_ids": [812, 813], "frame_ids": [5531]}}
```

**coverage** (full local version)

```json
{"lesson_id": "L-T1-20261017-1000", "teacher_id": "T1", "class_id": "4A", "syllabus_id": "fr-grammaire-4e", "syllabus_version": 1,
 "generated_at": "2026-10-17T11:05:00+02:00",
 "points": [{"kp_id": "KP03", "covered": true, "minutes": 4.5, "segment_ids": ["S-L-T1-20261017-1000-003"]}]}
```

**coverage\_share** (the only coverage format allowed to be uploaded; generated by C from `coverage`)

```json
{"lesson_id": "L-T1-20261017-1000", "class_id": "4A", "date": "2026-10-17", "syllabus_id": "fr-grammaire-4e", "syllabus_version": 1,
 "points": [{"kp_id": "KP03", "covered": true, "minutes": 4.5}]}
```

**quiz** (used only locally; the game page does not show each question's `source`)

```json
{"quiz_id": "Q-L-T1-20261017-1000", "lesson_id": "L-T1-20261017-1000", "class_id": "4A", "status": "pending", "style_profile_version": 2,
 "questions": [{"q_id": "Q1", "kp_id": "KP03", "type": "mcq", "prompt": "…", "choices": ["…", "…", "…", "…"], "answer": 1, "time_limit_s": 20,
   "source": {"segment_id": "S-L-T1-20261017-1000-003", "quote": "…teacher's words in class…", "frame_ids": [5531]}}]}
```

`type` values: `mcq` | `fill_blank` | `true_false`. For `mcq`, `answer` is the choice index; for `fill_blank` it is a string; for `true_false` it is a boolean. `status`: `pending` | `approved` | `rejected` | `published`.

**alerts**

```json
{"lesson_id": "L-T1-20261017-1000",
 "missed": [{"kp_id": "KP02", "note": "Planned in the lesson plan, not covered in this lesson or the past 21 days"}],
 "covered_before": [{"kp_id": "KP01", "last_covered_at": "2026-10-14T10:20:00+02:00"}],
 "weak_from_reports": [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]}
```

**style\_profile**

```json
{"teacher_id": "T1", "version": 2, "updated_at": "2026-10-17T11:06:00+02:00",
 "rules": [{"rule": "Prefers fill-in-the-blank questions", "origin": "screen_history", "evidence": {"frame_ids": [4410], "timestamp": "2026-10-15T14:20:00+02:00"}},
           {"rule": "Uses common student mistakes as distractors", "origin": "teacher_edit", "evidence": {"edit_ids": ["E3"]}}]}
```

**edit\_event** (one per line in `edits.jsonl`)

```json
{"edit_id": "E3", "quiz_id": "Q-L-T1-20261017-1000", "q_id": "Q1", "action": "edit", "before": {}, "after": {}, "at": "2026-10-17T11:20:00+02:00"}
```

`action`: `edit` | `delete` | `approve` | `reject`. `before` / `after` are full question objects.

**weights**

```json
{"class_id": "4A", "updated_at": "2026-10-17T12:00:00+02:00", "weights": {"KP03": 2.0, "KP01": 1.0}}
```

Weight rules: default 1.0; accuracy below 50% sets it to 2.0; weak points from Kahoot reports add 0.5.

**attempt**

```json
{"quiz_id": "Q-L-T1-20261017-1000", "nickname": "lapin42", "q_id": "Q1", "response": 2, "correct": false, "time_ms": 8400, "at": "2026-10-17T11:30:12+02:00"}
```

**kp\_stats**

```json
{"quiz_id": "Q-L-T1-20261017-1000", "class_id": "4A", "n_players": 18,
 "by_kp": [{"kp_id": "KP03", "accuracy": 0.41, "avg_time_ms": 12000}]}
```

**audit\_event**

```json
{"event_id": "EV-0007", "workspace_id": "W1", "actor": {"role": "teacher", "id": "T1"},
 "action": "share_coverage", "target_id": "L-T1-20261017-1000", "at": "2026-10-17T12:01:00+02:00"}
```

`action`: `join` | `consent` | `publish_quiz` | `share_coverage` | `revoke` | `approve_syllabus`.

## 6. Interfaces

### 6.1 chalkback-pipe (A + B)

The top of `pipe/pipe.md`:

```markdown
---
schedule: manual
enabled: true
timeout: 900
permissions:
  allow:
    - Content(audio, ocr, accessibility)
  deny:
    - App(1Password)
    - Window(*incognito*)
    - Window(*privée*)
---
```

- `schedule` is rewritten as cron by the console wizard based on the timetable (e.g. Monday–Friday 11:05 is `5 11 * * 1-5`), written via the screenpipe API `POST /pipes/chalkback/config`. For the demo, trigger manually with `npx -y screenpipe@latest pipe run chalkback`.
- Permissions: the official `reader` preset only allows a few endpoints such as `/search`, and **does not include `/raw_sql`**. So all data extraction uses `GET /search`. The custom rules above are a draft; A confirms them before hour 3 against the official docs and actual runs.
- Local API auth: every request carries `Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY` (injected automatically by screenpipe when running a pipe).
- Model: configured in screenpipe's AI preset; using Claude requires an Anthropic API key — a Pro/Max subscription won't work.

The pipe body runs in order:

1. Read the context header and `~/.chalkback/config.json`, determine the lesson that just ended (`lesson_id`, `class_id`, start and end time).
2. `python scripts/extract_segments.py --start <ISO> --end <ISO> --out <outbox>/segments.json` (A).
3. Generate `coverage.json` following `prompts/map_kp.md`, and validate it with `scripts/validate.py coverage` (A).
4. `python scripts/read_reports.py --days 7`: search screen text whose window title contains a Kahoot report, output weak knowledge points (A).
5. Compare against `lesson_plan` following `prompts/alerts.md`; for points not covered in this lesson, look back with `/search` explicitly specifying the past 21 days as the time range (the default lookback window is at most 8 hours); output `alerts.json` (B).
6. If `style_profile.json` doesn't exist, or `edits.jsonl` has new records: update the style profile following `prompts/learn_style.md` (B).
7. Generate `quiz.json` following `prompts/gen_quiz.md` using the coverage table, weights and style profile, each question with a `source`; then generate the student game page game.html from the template (reads quiz.json, submits answers to the console), and validate (B).
8. Write to the outbox, writing the `ready` marker file last; `POST http://localhost:11435/notify` to notify the teacher (B).

screenpipe endpoints used: `GET /search`, with parameters `content_type` (`audio` / `ocr` / `accessibility`), `start_time`, `end_time`, `app_name`, `window_name`, `q`, `limit`, `offset`. For audio results, use `device_type = input` to get only the microphone. Source screenshots are read locally by the console; the endpoint is per A's testing.

### 6.2 outbox file interface (B writes, C reads)

```
~/.chalkback/
  config.json                 # C writes, B reads
  cache/syllabus.json         # C pulls from Hub
  lesson_plans/{class_id}/{date}.json
  outbox/{lesson_id}/segments.json | coverage.json | alerts.json | quiz.json | game.html | ready
  state/style_profile.json | edits.jsonl | weights.json | shares.json | attempts.jsonl
```

Rules: C only processes directories that have a `ready` file; B does not modify a directory that already has `ready`. `config.json` example:

```json
{"hub_url": "https://<hub>", "token": "<from join>", "teacher_id": "T1", "workspace_id": "W1", "syllabus_id": "fr-grammaire-4e",
 "timetable": [{"day": "MON", "start": "10:00", "end": "11:00", "class_id": "4A"}], "auto_share": false, "consent_at": "2026-10-17T09:30:00+02:00"}
```

### 6.3 Teacher console (C)

Local `https://localhost:4000` (self-signed certificate generated by `console/generate_cert.py`; the first time it is opened the browser warns that the certificate is untrusted — just confirm and continue); all pages (including `/play` and the answer endpoint) only allow local access. The student game is only opened in the browser on the teacher's computer; no mobile version.

| Page | Function |
| --- | --- |
| `/setup` | Invite code → subject and class → timetable → informed consent (A1) → write `config.json` and pipe schedule |
| `/review` | List the outbox; show missed-point alerts; approve / edit / delete each question (A2); open a source to show the quote and screenshot; approve sharing coverage data (A3) |
| `/play/{quiz_id}` | Student game: serves the agent-generated `game.html` locally; receives answers and writes them to `attempts.jsonl`; aggregates by knowledge point to produce `kp_stats` and `weights.json` |
| `/shares` | Upload history (from `shares.json` and the Hub audit); withdraw (A5) |
| `/style` | Read-only display of the style profile and the source of each rule |

### 6.4 School Hub API (D)

All endpoints use HTTPS (Docker deployment is `https://<hub>:8443`, certificate generated by `hub/generate_cert.py`). Auth: the token returned by `POST /api/join`, sent as `Authorization: Bearer <token>`; each token maps to one role. Dashboard data comes only from coverage tables approved for upload.

| Method | Path | Role | Input | Output |
| --- | --- | --- | --- | --- |
| POST | `/api/join` | Anyone | `{invite_code, display_name, role}` | `{teacher_id, token, workspace_id}` |
| GET | `/api/syllabus/current` | All | — | `syllabus` |
| POST | `/api/syllabus` | Head | `syllabus` (draft) | `{syllabus_id, version}` |
| POST | `/api/syllabus/{id}/approve` | Head | — | `syllabus` (A4) |
| POST | `/api/syllabus/extract` | Head | `{filename, content_base64, syllabus_id?}` (PDF / DOCX / PPTX / TXT / MD, ≤ 5 MB) | `{syllabus, chunks, kept, new, dropped}`: an AI-suggested draft; saves nothing. Existing kp_ids are kept for the same points. `503` if neither `ANTHROPIC_API_KEY` nor `GEMINI_API_KEY` is set |
| POST | `/api/coverage` | Teacher | `coverage_share` | `{share_id}` (A3) |
| DELETE | `/api/coverage/{share_id}` | The teacher themself | — | `204` (A5) |
| GET | `/api/coverage?class_id=` | Per §4 permissions | — | Knowledge point coverage table (KPs covered / not covered for that class, with durations) |
| GET | `/api/dashboard?view=teacher\|head\|admin` | Matching role | — | Syllabus progress and warnings |
| GET | `/api/audit` | All, filtered by role | — | `audit_event[]` |

Warning rule (dashboard): when `remaining uncovered KPs > weeks left until exam × the class's past average KPs covered per week`, show "won't finish before the exam". The exam date is stored in the workspace settings.

## 7. Code repository structure

One GitHub repo `chalkback`; each directory has one owner, and only the owner merges changes to that directory.

```
chalkback/
  contracts/                 # shared by everyone; frozen at hour 3, changes require everyone's agreement
    *.schema.json
    examples/*.json          # one working sample per contract, the mock for each role
  pipe/                      # A + B (this directory is what gets installed via screenpipe pipe install)
    pipe.md                  # B
    scripts/extract_segments.py   # A
    scripts/read_reports.py       # A
    scripts/validate.py           # B
    prompts/map_kp.md             # A
    prompts/alerts.md             # B
    prompts/learn_style.md        # B
    prompts/gen_quiz.md           # B
    templates/game.html           # B: student game page template; the agent generates each lesson's game.html from it
  console/                   # C: local console (backend + frontend), including serving the student game and recording answers
  hub/                       # D: Hub backend, knowledge point coverage table, dashboard frontend, database
  demo/                      # A: demo data, lesson plans, syllabus, screen recording script
  docs/
    SETUP.md                 # B: install guide for new teachers
    ADMIN.md                 # D: guide for school admins and department heads
    DEMO.md                  # A: demo steps and fallback plan
```

## 8. Division of work

Four roles, layered by architecture. Task IDs `TA1`, `TB1`… are used in communication and commit messages (unrelated to approval points A1–A5). Deadlines correspond to the checkpoints in §10.

### Role A: memory and data layer

Responsible for pulling the lesson out of screenpipe and mapping it to knowledge points. Owns: `pipe/scripts/extract_segments.py`, `pipe/scripts/read_reports.py`, `pipe/prompts/map_kp.md`, `demo/`, `docs/DEMO.md`.

| Task | Deliverable | Acceptance criteria | Deadline |
| --- | --- | --- | --- |
| TA1 Install screenpipe on the two demo computers (teachers T1, T2); test the fields of `/search` and the permission rules | Test notes (field names, sample responses, whether permissions allow access) committed to `demo/` | The whole team can write code from them | Saturday 13:00 |
| TA2 `extract_segments.py`: fetch microphone transcription and slide text by time window, align by timestamp into segments (split on slide changes, ~2–5 minutes each) | Script | Output passes `segment` validation; runs under read-only permissions | Saturday 20:00 |
| TA3 `map_kp.md` prompt, generates `coverage.json` | Prompt + one real output | Output passes `coverage` validation | Saturday 20:00 |
| TA4 Mapping quality evaluation: manually label the knowledge points of one demo lesson and compare with the output | An accuracy number + explanation | Can go into the pitch | Sunday 09:00 |
| TA5 `read_reports.py`: read weak questions from the Kahoot report page's screen text and map them to knowledge points | Script | Outputs correct `weak_from_reports` for the demo report page | Sunday 01:00 |
| TA6 Demo data: agree on the syllabus with D; write lesson plans; T1 and T2 each record 2 lessons (including one "last week" lesson); T1 and T2 each manually write 3–4 question sets with clearly different styles on a quiz platform; T1 opens a Kahoot report page once | Real records in screenpipe + syllabus and lesson plans in `demo/` | B and C can integrate with real data | Saturday 20:00 |
| TA7 `DEMO.md`, fallback screen recording, organize rehearsal | Document + video | Two rehearsals, each under 3 minutes | Sunday 17:00 |

### Role B: agent and learning layer

Responsible for pipe orchestration, question generation, alerts, style learning and installation. Owns: `pipe/pipe.md`, `pipe/scripts/validate.py`, `pipe/prompts/alerts.md`, `pipe/prompts/learn_style.md`, `pipe/prompts/gen_quiz.md`, `docs/SETUP.md`.

| Task | Deliverable | Acceptance criteria | Deadline |
| --- | --- | --- | --- |
| TB1 `validate.py`: validate any contract file against `contracts/` | Script | All of `examples/` pass; invalid files raise errors | Saturday 13:00 |
| TB2 `pipe.md` orchestrates the 8 steps in §6.1 | pipe | `pipe run chalkback` with mock segments produces a complete outbox | Saturday 20:00 |
| TB3 `gen_quiz.md`: allocate question counts by coverage time and weights, only test covered knowledge points, each question with a `source`; then generate the student game page `game.html` from `templates/game.html` | Prompt + game template + real output | Passes `quiz` validation; each `source.quote` can be found in the transcript; `game.html` opens and can be answered in the browser on the teacher's computer | Saturday 20:00 |
| TB4 `alerts.md` + 21-day lookback | Prompt | Correctly distinguishes "not covered" from "covered last week" on demo data | Sunday 01:00 |
| TB5 `learn_style.md`: generate the style profile from the teacher's question-writing screens over the past 30 days (windows containing Kahoot, Quizlet, Forms) and `edits.jsonl`, each rule with evidence | Prompt + two style profiles for T1 and T2 | The two files are clearly different; questions generated from the same lesson differ in style | Sunday 09:00 |
| TB6 Packaging: pipe installable from GitHub with one command; write `SETUP.md` | Document + installable pipe | Installed on a clean computer by following the document | Sunday 09:00 |
| TB7 Newcomer test: have someone outside the team install by following `SETUP.md` and time it; fix the document based on issues | Timing result + revised document | A real number to cite in the pitch | Sunday 13:00 |

### Role C: teacher-facing and approval layer

Responsible for the UI teachers and students see, and all teacher-side approvals. Owns: `console/`.

| Task | Deliverable | Acceptance criteria | Deadline |
| --- | --- | --- | --- |
| TC1 Console skeleton, reads the outbox (mock first) | Runnable console | Lists mock lessons and questions | Saturday 13:00 |
| TC2 `/setup` wizard: join with invite code, timetable, informed consent page (A1), write `config.json`, write pipe schedule via the screenpipe API | Page | A new user completes setup without touching code; the audit has `join` and `consent` | Sunday 01:00 |
| TC3 `/review`: per-question review (A2), open source to show quote and screenshot, missed-point alerts, approve sharing (A3); write `edits.jsonl`; generate `coverage_share` and upload | Page | Uploaded content contains no raw text and no screenpipe ids | Saturday 20:00 (mock) / Sunday 01:00 (with Hub) |
| TC4 Student game `/play`: serve the agent-generated `game.html` locally (`localhost`); enter nickname, per-question timer, answers written to `attempts.jsonl` | Feature | All three question types can be answered; multiple students answering one after another on the same computer (different nicknames) are all recorded correctly | Sunday 01:00 |
| TC5 Locally aggregate `attempts.jsonl` by knowledge point into `kp_stats`, and generate `weights.json` per the rules in §5 | Feature | The next quiz uses the new weights | Sunday 09:00 |
| TC6 `/shares` share history and withdraw (A5); `/style` read-only style page | Page | After withdrawal the Hub dashboard no longer shows it, and the audit has `revoke` | Sunday 09:00 |

### Role D: school Hub and sharing layer

Responsible for everything shared across multiple people, deployment and the pitch slides. Owns: `hub/`, `docs/ADMIN.md`.

| Task | Deliverable | Acceptance criteria | Deadline |
| --- | --- | --- | --- |
| TD1 Deployment method and public URL; API skeleton returns mocks per §6.4 | Public URL + mock API | Opens in a browser on the public internet; C can integrate | Saturday 13:00 |
| TD2 Workspaces, invite codes, `/api/join`, role tokens | Endpoints | Each of the three roles can join | Saturday 20:00 |
| TD3 Syllabus drafts, head approval, versions (A4) | Endpoints + page | Unapproved versions don't take effect | Sunday 01:00 |
| TD4 Knowledge point coverage table: receive approved `coverage_share`, aggregate by class and grade, serve `/api/coverage` | Endpoints | Integration with TC3 uploads passes | Sunday 01:00 |
| TD5 Coverage data intake and withdrawal (A3, A5), audit log | Endpoints | Every approval and withdrawal has an `audit_event` | Sunday 01:00 |
| TD6 Three dashboard views + pre-exam warning + audit list | Page | After switching roles, visible content matches the permission table in §4 | Sunday 09:00 |
| TD7 `ADMIN.md`; pitch slides (including one slide on business model and privacy boundary) | Document + slides | Used in rehearsal | Sunday 13:00 |

## 9. Handoffs between roles

Each row is one handoff: before the due time the consumer develops against mocks; after it, they switch to the real output. When a handoff is done, the provider posts "handoff ID + location" in the group chat.

| ID | Provider → consumer | What is delivered | Due | Before then use |
| --- | --- | --- | --- | --- |
| H1 | Everyone → everyone | `contracts/` schema + examples, frozen | Saturday 13:00 | §5 of this document |
| H2 | A → everyone | screenpipe `/search` test notes (TA1) | Saturday 13:00 | Official docs |
| H3 | D → C | Hub public URL + mock API (TD1) | Saturday 13:00 | Local fake server |
| H4 | D + A → everyone | Demo syllabus `syllabus` | Saturday 13:00 | `examples/syllabus.json` |
| H5 | A → B | Real `segments.json` and `coverage.json` (TA2, TA3) | Saturday 20:00 | `examples/` |
| H6 | A → B, C | Real demo records in screenpipe (TA6) | Saturday 20:00 | — |
| H7 | B → C | Complete outbox (TB2, TB3) | Saturday 20:00 | `examples/` |
| H8 | C → D | Uploaded `coverage_share` (TC3) | Sunday 01:00 | Send examples with curl |
| H9 | B → C | Agent-generated student game page `game.html` (TB3) | Saturday 20:00 | Hand-written sample page |
| H10 | C → B | `edits.jsonl` (TC3), `weights.json` (TC5) | Sunday 01:00 / 09:00 | Hand-written sample files |
| H11 | B → everyone | Installable pipe + `SETUP.md` (TB6) | Sunday 09:00 | Install from a local folder |
| H12 | Everyone → A | Each person's demo segment works, for rehearsal and the fallback recording | Sunday 13:00 | — |

**Collaboration rules**

- The critical path is H5 → H7 → H8: a delay from A or B holds up end to end. If anyone expects to be more than 1 hour late, say so in the group chat immediately; everyone else keeps using mocks.
- Changing a contract: propose the fields and reasoning in the group chat → affected roles agree → update `contracts/`, examples and this document together.
- Hold a 5-minute standup at each checkpoint: everyone says what they finished, where they're stuck, and what they'll deliver by the next checkpoint.
- Put the task ID in commit messages, e.g. `TC3: approve flow writes edits.jsonl`.

## 10. Timeline and checkpoints

About 34 hours from now until submission. "Done" at each checkpoint must be demoable, not "code half written".

1. **Saturday 13:00 · Ready to start**: contracts frozen (H1); screenpipe tested (H2); Hub public URL and mock (H3); demo syllabus (H4); whole team settles the tech stack and LLM API key.
2. **Saturday 20:00 · Each part runs**: each component runs independently with mocks; demo lessons, question-writing screens and the Kahoot report page are recorded (H6).
3. **Sunday 01:00 · First end to end**: real recorded lesson → pipe → outbox → review → local game answers → stats → approve sharing to Hub. After that, take turns sleeping as needed.
4. **Sunday 09:00 · Track 3 feature complete**: five approval points, withdraw, audit log, three role views, style learning, `SETUP.md`.
5. **Sunday 13:00 · Feature freeze**: newcomer install test from outside the team (TB7); record the fallback demo video; finalize slides. Only bug fixes after this.
6. **Sunday 17:00 · Rehearsal**: run through fully twice, each run timed at 3 minutes or less; prepare Q&A material.
7. **Sunday 19:00 · Submit**.

Suggested staggered sleep: A and B sleep first after the first end to end; C and D keep working on approvals and dashboard early Sunday morning and catch up on sleep Sunday morning. Everyone gets at least 5 hours.

## 11. Demo script (3 minutes)

The storyline is "one teacher's workflow becomes automation the whole school can use". No live teaching; use pre-recorded data.

| Time | Screen | Key points to say | Owner |
| --- | --- | --- | --- |
| 0:00–0:15 | Title slide | Pain point; "the teacher teaches as usual, screenpipe remembers the lesson" | D |
| 0:15–0:35 | New teacher joins: one command from `SETUP.md` + setup wizard and informed consent page | "A newcomer from outside the team installed it in X minutes" (using the real number from TB7) | B |
| 0:35–1:10 | pipe output after class: missed-point alerts + quiz; open a question to show the quote and slide screenshot; side by side, the different styles T1 and T2 learned from the same pipe | One shared pipe, each teacher gets their own style | A |
| 1:10–1:35 | Teacher approves → open the game page locally and answer one question → answer stats (including pre-prepared whole-class answer data): "everyone got question 2 wrong, weight it up next time" | Nothing is published without review | C |
| 1:35–2:05 | Approve sharing → switch dashboard across three roles: teacher, head, admin; pre-exam warning | Different roles see different content; adjust course in time | D |
| 2:05–2:30 | Audit log → teacher clicks "withdraw" → dashboard updates | Every share is teacher-approved, traceable and withdrawable; recordings never left the computer | C |
| 2:30–3:00 | Architecture diagram + business model slide | Schools subscribe annually; can be deployed school-wide via screenpipe Teams | D |

Q&A material (recordings ready): style profile v1→v2 after the teacher edits questions, and regeneration; looking back over the past 21 days to avoid false alerts; reading the Kahoot report; head approves a new syllabus version; mapping accuracy (TA4); asking questions in Claude via MCP.

## 12. Risks and open questions

| Risk or question | Response | Owner | Deadline |
| --- | --- | --- | --- |
| Whether the competition requires choosing a track, and whether prizes are by track | Ask the on-site organizers | D | Saturday 13:00 |
| Some endpoints unavailable under read-only permissions | Only use `/search`; adjust permission rules per TA1 testing | A | Saturday 13:00 |
| Screen text quality: on Linux it relies mainly on OCR | Use Windows or macOS for the demo computers | A | Saturday 13:00 |
| LLM API key and cost | Settle on model and provider; configure in the screenpipe AI preset; key stays out of the repo | B | Saturday 13:00 |
| Demo lesson subject, grade, language and syllabus not decided | Whole team picks one concrete topic, with 8–12 knowledge points | A + D | Saturday 13:00 |
| Knowledge point mapping inaccurate | Validate on one lesson first (TA3, TA4); add keyword rules as a fallback if needed | A | Saturday 20:00 |
| pipe timeout or lookback window too short | `timeout: 900`; explicitly specify start and end times in prompts | B | Saturday 20:00 |
| The game is only answered on the teacher's computer, so few people answer live and stats and weights aren't noticeable | Prepare a whole-class `attempts.jsonl` with multiple nicknames in advance as demo data; only demo answering one question live | C | Saturday 20:00 |
| Kahoot report page read inaccurately | Treat it only as a bonus; learning stats come mainly from our own game data | A | Sunday 01:00 |
| Network or program problems on site | Fallback recording; generate all demo data in advance | A | Sunday 13:00 |
| Judges question "surveilling teachers" | In the pitch, proactively present the §4 permission table and privacy boundary; only the teacher's microphone is recorded, students use nicknames only | D | Sunday 13:00 |
| UI language (French or English) not decided | Decide based on the judges' makeup | Everyone | Saturday 13:00 |

## 13. Open items

Moved to [`TODO.md`](./TODO.md): open items per role, team decisions still needed, and what has been fixed.
