# ChalkBack

A teaching assistant for schools: screenpipe remembers the lesson on each teacher's computer, and after class chalkback-pipe generates quizzes, a student game, missed-point alerts and learning stats;
after the teacher's approval, only syllabus coverage data reaches the school Hub. screenpipe hackathon Track 3.

**The full design is in [`DESIGN.md`](./DESIGN.md); it is the single source of truth.**

## Directories and owners (§7)

Only the owner merges changes to a directory.

| Directory | Owner | Contents |
| --- | --- | --- |
| `contracts/` | Everyone | JSON Schema + examples. Frozen Saturday 13:00; changes need everyone's agreement |
| `pipe/` | A + B | chalkback-pipe; this is what `screenpipe pipe install` installs |
| `pipe/scripts/extract_segments.py`, `read_reports.py`, `prompts/map_kp.md` | A | Fetch data, map to knowledge points |
| `pipe/pipe.md`, `scripts/validate.py`, `prompts/{alerts,learn_style,gen_quiz}.md`, `templates/` | B | Orchestration, quiz generation, alerts, style |
| `console/` | C | Teacher console :4000 (approvals A1–A3, initiates A5) |
| `hub/` | D | School Hub (approval A4, executes A5) |
| `demo/`, `docs/DEMO.md` | A | Demo data and script |
| `docs/SETUP.md` | B | Install guide for new teachers |
| `docs/ADMIN.md` | D | Guide for admins and department heads |
| `tools/`, `tests/`, `Makefile` | Everyone | Dev helpers, contract self-checks |

## Getting started

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
make check          # all examples pass the contracts + component tests
make hub            # https://localhost:8000, test mode (mock token, DEMO-* invite codes)
make teacher        # https://localhost:4000/console, reads .mock-home
make mock-local     # optional, with both running: load the demo data into them (see below)
```

If upstream isn't done yet, start with the mocks in `contracts/examples/`; don't wait.

### With Docker

```bash
make up             # = docker compose up --build -d
                    # Hub https://localhost:8443 (API at /docs), console https://localhost:4000
make mock           # optional: load the demo data into the running Hub + console
make down           # stop, data is kept
make reset          # also delete the data volumes; the next up starts empty
```

**Mock data only exists if you ask for it.** `make up` (and `make hub` / `make teacher`) start empty: the Hub has no
syllabus, no lessons and no courses, and the console shows "Not set up yet". `make mock` (or `make mock-local`) loads
the demo data through the real API:
- Hub: the French syllabus (main) and a maths syllabus, approved by department head H1; 9 shared lessons in classes 4A,
  4B and 4C (4B triggers the exam alert); 5 courses, 3 of them with a summary sent to the department head.
- Console: a mock `~/.chalkback/` from `contracts/examples` (teacher T1, one lesson with its quiz).

You can run it again: the Hub keeps what it has and adds what is missing, while the console's data is replaced by the
mock. To start from nothing, `make reset` then `make up`. Sign in with the `DEMO-*` invite codes (test mode only).

- The containers hold only **the Hub + console (mock data)**. screenpipe and chalkback-pipe must run on the teacher's computer (they record the mic and screen) and do not go in a container.
- The console container binds only `127.0.0.1:4000`. The student game also opens only on the teacher's computer; there is no mobile version.
- In a real deployment, the console runs directly on the teacher's computer without Docker; the Hub can be deployed to the cloud with `hub/Dockerfile`.

## Rules at a glance

- The contracts (§5, §6) are hard constraints; do not change them on your own. After changing `contracts/`, remember to run `make sync-schemas`.
- Recordings, screenshots, raw transcripts and screenpipe ids never leave the teacher's computer; the only upload is `coverage_share`.
- All times are ISO 8601 with a timezone offset (Europe/Paris). Code, field names and file names are in English.
- Put the task ID in commit messages: `TC3: approve flow writes edits.jsonl`.
