<!--
  Owner: B (TB6, TB7). Goal: a teacher who has never seen the project can follow this page without touching code.
  Items marked "to verify" must be checked on a clean laptop before the demo (TB6 acceptance), then the marks removed.
-->

# ChalkBack — setup for teachers

ChalkBack turns each of your lessons into a short quiz game for your students, reminds you of syllabus points
you planned but did not cover, and — only when you approve it — shares which syllabus points each class has covered
with your department.

**Time needed:** about 30–40 minutes, much of it waiting for downloads. **You need:**

- a Windows 10/11 or macOS 13+ laptop that you teach with,
- the **invite code** from your school administrator,
- an **AI key** — either the one your school gives you, or your own Anthropic API key
  (a Claude Pro/Max subscription does not work here).

## What stays on your laptop, what is shared

| | Where it goes |
| --- | --- |
| Your microphone audio, screenshots and transcripts | **Never leave your laptop.** |
| Generated quizzes, students' answers, your quiz style | Stay on your laptop. Students only type a nickname. |
| Which syllabus points a class covered, and for how long | Sent to the school Hub **only after you click approve** — and you can withdraw it at any time. |

You will be asked to agree to this in the setup wizard (step 5).

---

## Step 1 — Install screenpipe (5 min)

screenpipe is the app that remembers your lessons locally.

1. Download the desktop app from <https://screenpipe.com> and install it.
2. Open it and allow the permissions it asks for: **microphone** and **screen recording**
   (macOS: *System Settings → Privacy & Security*).
3. Leave it running. It must be running during your lessons.

## Step 2 — Add your AI key to screenpipe (2 min)

In screenpipe, open **Settings → AI** and add an AI preset with your key
(Anthropic: choose a Claude model). ChalkBack uses this preset; the key is never stored by ChalkBack.

## Step 3 — Install Node.js and Python (3 min)

ChalkBack's installer needs **Node.js**, and its helper scripts need **Python 3.11 or newer**.
Skip whatever you already have (`node --version`, `python --version`).

**Windows** — open *Terminal* (or PowerShell) and run:

```powershell
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
```

Then **close and reopen the terminal**. If `python --version` opens the Microsoft Store instead, go to
*Settings → Apps → Advanced app settings → App execution aliases* and turn off both *python* entries.

**macOS** — install Node.js from <https://nodejs.org> (LTS) and Python from <https://www.python.org/downloads/>,
or with Homebrew: `brew install node python@3.12`.

## Step 4 — Install ChalkBack (1 command)

```bash
npx -y screenpipe@latest pipe install https://github.com/wangunuxe/Chalkback/tree/main/pipe
```

Check that it is there:

```bash
npx -y screenpipe@latest pipe list
```

You should see **chalkback** in the list. *(to verify: the pipe may be listed as `pipe` — if so, use that name below.)*

<details>
<summary>If the install command fails</summary>

Download the project as a ZIP from <https://github.com/wangunuxe/Chalkback> (*Code → Download ZIP*), unzip it,
then install from the folder:

```bash
npx -y screenpipe@latest pipe install ./Chalkback-main/pipe
```
</details>

## Step 5 — Start the ChalkBack console and run the setup wizard (5 min)

The console is a small web page that runs on your laptop. Only your laptop can open it — your students also
play the quiz game on your laptop, one after another.

1. If you have not already, download the project as a ZIP from <https://github.com/wangunuxe/Chalkback>
   (*Code → Download ZIP*) and unzip it.
2. Open a terminal in the unzipped folder, then install the console once:

   **macOS**

   ```bash
   cd Chalkback-main/console
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

   **Windows**

   ```powershell
   cd Chalkback-main\console
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```

3. Start the console (do this again whenever you want to use it; keep the terminal open while you do):

   **macOS**

   ```bash
   .venv/bin/python generate_cert.py
   .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```

   **Windows**

   ```powershell
   .venv\Scripts\python generate_cert.py
   .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```

4. Open <https://localhost:4000/setup>. The first time, your browser says the connection is not private: the
   certificate was made by your own laptop, so this is expected. Click *Advanced → Proceed to localhost*.

<!-- TODO(C): /setup currently has only a JSON API, no wizard page yet (TODO.md §5). Check the four steps below once the wizard is done. -->
Follow the four screens:

1. **Invite code** — joins your school's workspace.
2. **Subject and classes** you teach.
3. **Timetable** — when each class meets. ChalkBack runs automatically a few minutes after each lesson ends.
4. **Consent** — read what is recorded and what is shared, and agree.

## Step 6 — Check everything (1 min)

```bash
python ~/.screenpipe/pipes/chalkback/scripts/doctor.py
```

On Windows: `python %USERPROFILE%\.screenpipe\pipes\chalkback\scripts\doctor.py`
(on macOS use `python3` if `python` is not found). *(to verify: install folder and name.)*

Every line should start with `[ok]` (a `[warn]` is fine). For each `[FAIL]`, do what its `fix:` line says
and run the check again. The last line must read **All required checks passed.**

## Step 7 — Try it once (optional)

After a lesson — or after talking for a few minutes with a slide open — run:

```bash
npx -y screenpipe@latest pipe run chalkback
```

You will get a notification when it is done (1–5 minutes). Open <https://localhost:4000/console>.

---

## Every day

Nothing to do: teach as usual with screenpipe running. After each lesson you get a notification. Then start the
console (step 5.3) and open <https://localhost:4000/console>:

1. **Review the quiz** — approve, edit or delete each question (click a question's source to see what you said in class).
2. **Publish** — then click *Open game*. Students play in your laptop's browser, one after another, each with a nickname.
3. **Approve sharing** of the syllabus coverage with your department, if you want to.
4. Changed your mind? Click *Withdraw* next to anything you shared.

The more you edit questions, the more ChalkBack writes them your way (see <https://localhost:4000/style>).

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `python` or `npx` is "not recognized" / "command not found" | Close and reopen the terminal after step 3. On macOS try `python3`. On Windows, turn off the App execution aliases (step 3). |
| doctor: `[FAIL] screenpipe ... not reachable` | Start the screenpipe app and wait until it shows it is recording. |
| doctor: `[FAIL] Teacher config` or `Syllabus` | Finish the setup wizard at <https://localhost:4000/setup>, then open the console once. |
| doctor: `[warn] Time zone` | Fine if your laptop is set to Paris time. Otherwise run `python -m pip install tzdata`. |
| No notification after a lesson | Check the timetable in the setup wizard. Run step 7 by hand and look at `npx -y screenpipe@latest pipe logs chalkback`. |
| "Failed to extract accountId" in the logs | Your AI preset is not set: redo step 2. |
| The browser says the connection is not private | Expected: the console uses a certificate made by your own laptop. Click *Advanced → Proceed to localhost*. |
| The game page says *Not Found* | Publish the quiz first in the console; only published quizzes can be played. |
| `localhost:4000` does not open | The console is not running: start it again (step 5.3). |
| The quiz says "nothing to quiz" | ChalkBack did not recognise any syllabus point in the lesson — check that your slides were on screen and your microphone was picked up. |

## Uninstall

```bash
npx -y screenpipe@latest pipe delete chalkback
```

Your ChalkBack data is in the `.chalkback` folder in your home folder; delete it to remove everything.

---

## New-user test log (TB7)

For the tester: follow this page from the top **without help**, time each step, and note anything that made you hesitate.

| Date | Tester | System | Step 1 | 2 | 3 | 4 | 5 | 6 | Total | Where they got stuck |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | | | |
