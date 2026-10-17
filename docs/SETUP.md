<!--
  Owner: B (TB6, TB7). Goal: a teacher who has never seen the project can follow this page without touching code.
  Items marked "to verify" must be checked on a clean laptop before the demo (TB6 acceptance), then the marks removed.
-->

# ChalkBack — setup for teachers

ChalkBack turns each of your lessons into a short quiz game for your students, reminds you of syllabus points
you planned but did not cover, and — only when you approve it — shares which syllabus points each class has covered
with your department.

**Time needed:** about 15 minutes. **You need:**

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

## Step 5 — Open the ChalkBack console and run the setup wizard (3 min)

<!-- TODO(C): replace with the real way a teacher starts the console (installer, app, or one command). -->
Start the ChalkBack console *(start instructions provided by the console team)*, then open
<http://localhost:4000/setup> in your browser and follow the four screens:

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

You will get a notification when it is done (1–5 minutes). Open <http://localhost:4000/review>.

---

## Every day

Nothing to do: teach as usual with screenpipe running. After each lesson you get a notification. Then, in
<http://localhost:4000/review>:

1. **Review the quiz** — approve, edit or delete each question (click a question's source to see what you said in class).
2. **Publish** — show the QR code; students scan it with their phone on the school Wi-Fi and play.
3. **Approve sharing** of the syllabus coverage with your department, if you want to.
4. Changed your mind? Withdraw anything you shared in <http://localhost:4000/shares>.

The more you edit questions, the more ChalkBack writes them your way (see <http://localhost:4000/style>).

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `python` or `npx` is "not recognized" / "command not found" | Close and reopen the terminal after step 3. On macOS try `python3`. On Windows, turn off the App execution aliases (step 3). |
| doctor: `[FAIL] screenpipe ... not reachable` | Start the screenpipe app and wait until it shows it is recording. |
| doctor: `[FAIL] Teacher config` or `Syllabus` | Finish the setup wizard at <http://localhost:4000/setup>, then open the console once. |
| doctor: `[warn] Time zone` | Fine if your laptop is set to Paris time. Otherwise run `python -m pip install tzdata`. |
| No notification after a lesson | Check the timetable in the setup wizard. Run step 7 by hand and look at `npx -y screenpipe@latest pipe logs chalkback`. |
| "Failed to extract accountId" in the logs | Your AI preset is not set: redo step 2. |
| Students cannot open the game | Their phones must be on the same network as your laptop. If the school Wi-Fi isolates devices, turn on your laptop's hotspot and have students join it. |
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
