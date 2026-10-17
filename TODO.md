# ChalkBack — open items

Open items found by checking the repo item by item against DESIGN.md §3–§12 (2026-10-17, based on `main` @ `d9e5db6`), updated after the fixes for roles A, B, C and D. `make check` passes (289 tests: 39 contract, 153 pipe, 47 console, 50 Hub); below are the parts tests don't cover, or that the design doc requires but haven't been done. Tick an item when it's done; add new findings as they come up.

## 1. Needs a team decision (touches contracts or interfaces; per DESIGN.md §0 requires unanimous agreement)

- [ ] **Audit for A1, A2**: `audit_event` has `consent` and `publish_quiz`, but DESIGN.md §6.4 has no endpoint to write them to the Hub, so neither DESIGN.md §4's "each approval writes one audit_event" nor TC2's acceptance can be met. Pick one: add `POST /api/audit` (accepting only these two), or change DESIGN.md §4 so A1 and A2 are only recorded locally. (C + D)
- [ ] **Head's "own grade" permission**: the contracts have no class → grade mapping, and the Hub currently lets the head see the whole school. Once decided, update DESIGN.md §4 or add a field. (D)
- [ ] **Exam date**: DESIGN.md §6.4 says it's stored in workspace settings, but there is no settings endpoint; currently it can only be set via the environment variable `HUB_EXAM_DATE` (default `2026-12-18`). (D)
- [ ] **Timed-out answers**: the game submits `response: null` on timeout and the console records it as wrong, but the `attempt` schema doesn't allow null (`pipe/templates/game.html:11`). (B + C)
- [ ] Write the **fill-in-the-blank grading rule** (ignore case and extra whitespace) into `contracts/` (`pipe/scripts/check_quiz.py:15`). The console already grades directly with this rule. (B + C)
- [ ] **Demo topic and syllabus**: still a 4-KP French placeholder, while DESIGN.md §12 calls for 8–12; `demo/syllabus/` is empty (H4). (A + D)
- [ ] LLM provider, model and cost cap not recorded. (B)
- [ ] UI language (French or English). (Everyone)
- [ ] Whether a track must be chosen: ask the organizers and record the answer. (D)

## 2. Blocks the demo, fix first

- [x] **Console HTTPS doesn't run on the host machine**: `console/generate_cert.py` now writes to its own `console/` directory and doesn't regenerate if a certificate exists; `make teacher` tested on macOS, `https://127.0.0.1:4000` works. (C)
- [x] **Hub HTTPS doesn't run on the host machine**: `hub/generate_cert.py` writes to its own directory, `make hub` switched to HTTPS. (D)
- [x] **`edits.jsonl` doesn't match `edit_event`**: the console now writes full `edit_event`s (`edit_id`, `quiz_id`, `before`, `after`), which pipe step 6 `style_inputs.py` can read; `setup.py` and `shares.py` no longer write non-contract records. (C)
- [x] **TC5 not implemented**: after each answer, recompute `state/kp_stats/{quiz_id}.json` and `state/weights.json` (default 1.0; accuracy < 50% → 2.0; Kahoot weak point +0.5). (C)
- [x] **Timed-out answers graded as correct**: now always counted as wrong; `mcq` no longer treats `true` as index 1. (C)
- [x] **Review only logged**: approve, edit, delete and reject all rewrite `quiz.json`; `game.html` is regenerated on publish; only published quizzes can be opened at `/play` (A2); the review page has review, publish, share and withdraw buttons. (C)
- [x] **Shows success when sharing fails**: returns 502 when the Hub is unreachable or rejects, with nothing recorded locally; on withdraw, the local record is deleted only after the Hub deletion succeeds. (C)
- [x] **`read_reports.py` invents weak points**: now outputs `[]` when no report is found, and on error writes `[]` and exits 1. (A)
- [x] **Public Hub security**: mock tokens and `DEMO-*` invite codes are off by default and only available in test mode; the home page no longer exposes invite codes. (D) The console also no longer falls back to `mock-token-T1` (C). Production mode has no mock T1, so a really joined T1 won't be confused with it.
- [x] **lesson_id of mock segments**: `extract_segments.py --mock` now uses `--lesson-id` and `--start`, so the outbox directory name matches the `lesson_id` in the files. (A)
- [x] **Mock timetable inconsistent**: `current_lesson.py --mock` always handles the Monday lesson after the sample lesson, and the seed writes a lesson plan for it. (B)

## 3. Role A

Fixed (pipe tests increased from 117 to 150):

- [x] TA2 `extract_segments.py`: slides shorter than 2 minutes are merged into adjacent segments, those longer than 5 minutes are split evenly; text from email, chat, password manager and similar windows is always discarded, and brief screens from other apps don't go into `slide_text`; no longer invents `app_name` (empty string when unknown); times unified to Europe/Paris; segments with no speech are not output, and if the whole lesson has no speech it outputs `[]`; also reads accessibility text (only ocr when older screenpipe doesn't support it); keeps at most 5 screenshot ids per segment; `device_type` is case-insensitive; `--mock` uses this lesson's `lesson_id` and times; added unit tests.
- [x] TA3 `prompts/map_kp.md` spells out the judgment rules (teacher's own words take precedence, passing mentions don't count, at most 2 knowledge points per segment, keyword fallback), the algorithm for minutes and `covered`, and that `lesson_id` / `teacher_id` / `class_id` come only from `$WORK/lesson.json`; added `scripts/check_coverage.py` to check these rules. `demo/coverage.json` changed to be consistent with `demo/segments.json`.
- [x] TA5 `read_reports.py`: no longer invents weak points (outputs `[]` when no report is found; writes `[]` and exits 1 when it can't read the syllabus or reach screenpipe); finds Kahoot pages by window title with pagination; finds questions with accuracy < 50% line by line, without tagging tied knowledge points; whole-word matching; no built-in subject keywords; no longer crashes on Windows without `tzdata`; added `--mock`; added unit tests.
- [x] TA6 lesson plan moved to `demo/lesson_plans/4A/2026-10-17.json` (where `current_lesson.py` looks).
- [x] `demo/screenpipe_test_record.md` closes the unclosed code block and lists items not yet tested.

Not done yet:

- [ ] TA1 testing: real responses for ocr and accessibility, `device_type` case, whether `window_name` matches by substring, `Api(...)` permissions, `/notify`, the source screenshot endpoint, and whether `deny` rules apply to capture or to reading (checklist in section 3 of `demo/screenpipe_test_record.md`). After testing, come back and confirm the parsing in `extract_segments.py` and `read_reports.py`.
- [ ] TA2 acceptance "runs under read-only permissions": needs one run with the real pipe on the demo computer.
- [ ] TA4 no manual labeling and no accuracy number.
- [ ] TA6 demo data: T2's lesson plan and the "last week" lesson; recorded lessons, question-writing screens and Kahoot report page can't be confirmed from the repo.
- [ ] TA7 steps, fallback plan and rehearsal notes in `docs/DEMO.md` are still empty; fallback recording; two rehearsals.

## 4. Role B

Fixed (pipe tests increased to 153):

- [x] Mock timetable inconsistent: `current_lesson.py --mock` fixes "now" to 2026-10-19 11:05 (sample timetable Monday 10:00–11:00), and `tools/seed_mock_home.py` also writes a lesson plan for that lesson; the mock notes in `pipe.md` now include `current_lesson.py`. Verified that the scripts for steps 0–7 chain together in a local mock run.
- [x] `lookback.py` now uses `extract_segments.is_mic()` to detect the microphone (`device_type` case-insensitive). (`style_inputs.py` only reads screen text, so it's not affected.)
- [x] `check_quiz.py`: also warns when `source.quote` exceeds 25 words.
- [x] `pipe.md` step 4 changed to "`read_reports.py` has already written `[]` when it exits with code 1"; mock notes now include `read_reports.py --mock` (changed by A, confirmed by B).
- [x] `docs/SETUP.md` step 5 explains how the teacher starts the console (virtual environment + `generate_cert.py` + `uvicorn`; tested to start following the instructions) and explains the certificate warning on first open; time changed to 30–40 minutes, consistent with the test card.

Not done yet:

- [ ] TB2 no record of `pipe run chalkback` having the agent actually run through once and produce a complete outbox (needs screenpipe and an AI preset). In mock mode `lookback.py` doesn't search, so all candidates become "missed" — this is by design for mock, not a bug.
- [ ] TB3 no `quiz.json` and `game.html` actually generated from demo data yet.
- [ ] TB4 acceptance (distinguishing "not covered" from "covered last week") needs real recorded lesson data (H6).
- [ ] TB5 missing two clearly different style profiles for T1 and T2.
- [ ] TB6 testing: the pipe's name after install (`chalkback` or `pipe`), whether the `tree/main/pipe` URL can be installed, the port and request body of `/notify` (TODO in `pipe/pipe.md`).
- [ ] TB7 newcomer test not done; timing result empty.
- [ ] Test once that a pipe run takes less than `timeout: 900`.
- [ ] Before changing `pipe/scripts/build_game.py` or `check_quiz.normalize_answer`, tell C first: the console reuses these two functions directly for publishing the game and grading (`console/app/contracts.py`).

## 5. Role C

Fixed (console tests increased from 8 to 47; endpoints in `console/README.md`):

- [x] TC3: missed-point alerts shown in three categories (not covered, covered before, Kahoot weak points), with knowledge points showing their syllabus title; `/console` no longer falls back to made-up fake data; validated against the `coverage_share` schema before upload; re-sharing replaces the old local record (consistent with Hub).
- [x] TC4: nonexistent or unpublished `quiz_id` returns 404 (was 500); fill-in-the-blank graded with the pipe's `normalize_answer`; answer times in Europe/Paris.
- [x] TC2 `/setup` issues: requires explicit `consent: true`; returns 502 when the Hub is unreachable, without writing a mock token; `workspace_id` taken from the join response; pulls and caches `cache/syllabus.json`.
- [x] `/console` no longer depends on the Tailwind CDN and Google Fonts (inline CSS, works offline).
- [x] All pages (including `/play`) only allow local access; `make teacher` and `make console` bind to `127.0.0.1`.
- [x] Added tests: `/review`, `/play`, `/shares`, `/setup` and the review page.
- [x] Deleted the outdated `verify_tc1.py`.
- [x] `console/README.md` documents all endpoints, the answer endpoint and the `state/shares.json` format.
- [x] Certificate private keys `*.pem` added to `.gitignore`.

Not done yet:

- [ ] TC2 HTML wizard for `/setup` (GET currently returns JSON), the subject and class steps, and the informed consent explanation page.
- [ ] TC2 write the pipe schedule from the timetable (generate cron, `POST /pipes/chalkback/config`): waiting on B testing the pipe's name after install (TB6 under Role B).
- [ ] TC3 show screenshot in source: waiting on A testing the screenshot endpoint (TA1 under Role A).
- [ ] TC6: `/shares` merging the Hub audit; `/style` only returns JSON, no read-only page.
- [ ] Entry point for teachers to fill in lesson plans (`lesson_plan`); `config.auto_share` is not used.
- [ ] Prepare whole-class `attempts.jsonl` demo data with multiple nicknames (DESIGN.md §12).

## 6. Role D

Fixed (Hub tests increased from 40 to 50):

- [x] Hub defaults to production mode: doesn't accept `mock-token-*`, public `DEMO-*` invite codes are disabled (existing ones in the DB are also deleted); the school's invite codes are set with `HUB_INVITES`. `make hub` and `docker-compose.yml` explicitly enable test mode (`HUB_MOCK_AUTH=1`); `hub/Dockerfile` doesn't.
- [x] Hub home page no longer publicly shows `DEMO-*` invite codes.
- [x] TD2 member IDs now "existing max ID + 1"; when two people joining at once collide, it recomputes instead of returning 500.
- [x] TD4 `POST /api/coverage` checks that the teacher in `lesson_id` is the uploader, that the syllabus version is approved, and that the knowledge points are in that version; otherwise 422.
- [x] `hub/generate_cert.py` writes to its own directory; `make hub` changed to `https://localhost:8000`, tested on macOS (`seed_demo.py` also runs through).
- [x] Docs: refresh interval in `docs/ADMIN.md` and `hub/README.md` changed to 3 seconds, documenting production mode, `HUB_INVITES`, upload checks and public certificates; `make hub` instructions in `README.md` updated.

Not done yet:

- [ ] TD1 / H3 public deployment and URL (when deploying, set `HUB_INVITES`, don't set `HUB_MOCK_AUTH`, and use a proper certificate).
- [ ] TD2 admin has no page to create workspaces or rotate invite codes (currently only by changing `HUB_INVITES` and restarting; old codes must be deleted from the DB manually).
- [ ] Syllabus version numbers and the "current syllabus" are computed globally per syllabus / workspace: fine for one school and one subject, but multiple workspaces or subjects need a schema change.
- [ ] TD7 slides (title slide, architecture diagram, business model, privacy boundary) are not in the repo; status unknown.

## 7. Places to sync after dropping mobile and switching to HTTPS

Team decision: the student game is only opened in the browser on the teacher's computer, no mobile version; the console and Hub both use HTTPS.

- [x] Console code, tests, `Makefile`, `console/README.md`, `README.md`, `docker-compose.yml` updated. (C)
- [x] This document updated for the local game and HTTPS: DESIGN.md §2, DESIGN.md §3 steps 7–8, DESIGN.md §6.3, DESIGN.md §6.4, DESIGN.md §8 TB3 / TC4 / TD1, DESIGN.md §10 item 3, DESIGN.md §11 rows 0:00 and 1:10, and the corresponding risk in DESIGN.md §12. (Everyone)
- [x] `docs/SETUP.md` (QR code, phone, hotspot), `pipe/prompts/gen_quiz.md` ("answer on your phone", "one phone screen"), `pipe/templates/game.html` (reason for not referencing external resources changed to working offline). (B)
- [x] Phone connection checks in `docs/DEMO.md` changed to the local game and whole-class answer data. (A)
- [x] http to https: notification link in `pipe/pipe.md`, `pipe/scripts/doctor.py`, `docs/SETUP.md`. (B)

## 8. DESIGN.md itself

- [ ] The DESIGN.md §2 architecture diagram was lost on export (`&#91;embedded content…`); could reference `workflow.webp` in the repo instead.
- [ ] DESIGN.md §6.1 frontmatter and steps don't match `pipe/pipe.md`: missing `Api(...)` permissions, step 0 `doctor.py`, step 1 `current_lesson.py`, and the `read_reports.py` arguments; `game.html` actually embeds the questions with answers stripped into the page, rather than reading `quiz.json`.
- [ ] DESIGN.md §6.2 is missing the storage locations of `work/{lesson_id}/` and `state/kp_stats/`; the DESIGN.md §5 contract table is missing `config`; in the DESIGN.md §5 `weights` example, KP03 should be 2.5 per the rules.
- [ ] DESIGN.md §7 repo structure is missing `pipe/schemas/`, `pipe/tests/`, the other scripts, `tools/`, `tests/`, `Makefile`, `docker-compose.yml`.
- [ ] Add "`make check` passes" to the DESIGN.md §0 "definition of done"; unify "before hour 3" into a specific time.
