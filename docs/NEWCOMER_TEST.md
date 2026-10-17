# TB7 newcomer install test procedure

Owner: B. Goal (design doc §8 TB7): have someone outside the team install ChalkBack using only `docs/SETUP.md`, record the real time taken,
then fix the docs wherever they got stuck. The resulting numbers are used in demo 0:15–0:35 (B presents) and in the pitch slides.

**Deadline: Sunday 13:00** (feature freeze after that).

| Time | What | Who |
| --- | --- | --- |
| Before Sunday 09:00 | Pre-test checks (section 1), including a full run-through yourself in a clean environment (this is also TB6's acceptance) | B |
| ~10:00 | The actual test, allow 45 minutes (sections 3, 4) | B hosts, tester |
| 10:45–12:00 | Sort issues, fix SETUP.md (section 5); a second tester if time allows | B |
| Before 12:30 | Send the numbers to D (slides) and A (`docs/DEMO.md`) (section 6) | B |

---

## 1. Pre-test checks (start only when everything is ticked)

Starting the test with known blockers unresolved just wastes the tester's time, and the numbers won't be usable.

- [ ] No `TODO` or *to verify* left in `SETUP.md`: from the repo root, `grep -n "TODO\|to verify" docs/SETUP.md` returns nothing
  - [ ] Step 5: C has written how teachers start the console
  - [ ] Step 4: confirm the pipe's name after install (`chalkback` or `pipe`), update SETUP if needed, and tell C
  - [ ] Step 6: confirm the pipe's install directory
- [ ] **B does a dry run**: in a clean environment, follow SETUP from the top until `All required checks passed`, and record your own time as a baseline
- [ ] The Hub's public URL opens (D)
- [ ] D has generated a **dedicated invite code** for the tester (role teacher), deleted after the test
- [ ] Prepare a **test-only AI key** with a spending cap, revoked after the test. Don't give the tester your personal key
- [ ] Test computer: ideally the tester's **own computer**; otherwise **create a new OS user** on some computer
  (macOS: System Settings → Users & Groups; Windows: Settings → Accounts → Other users).
  If that computer already has Node.js or Python installed, note it down: step 3 will be faster because of it
- [ ] The network at the test location can download things (screenpipe, Node.js and Python installers add up to several hundred MB)
- [ ] Timer: phone stopwatch; with consent, also record the screen (it can double as backup demo footage)
- [ ] Print or send the tester: the **tester card** at the end of this doc, the `SETUP.md` link, the invite code, the AI key

## 2. Finding a tester

- **Who**: someone outside the team who has never seen this project and uses a computer normally. A teacher or a non-coder is best, closest to the real user.
- **When scheduling, be clear**: about 40 minutes, on their own computer; screenpipe will be installed during the test (it records the screen and microphone),
  and we will help uninstall everything afterwards.
- The tester card (at the end) is in English and can be sent in advance.

## 3. Test day: what the host does

### Opening (2 minutes)

Go through the tester card with the tester, stressing three things:
1. We are testing the **guide**, not you: if you get stuck, the guide is badly written.
2. Please **think aloud** as you go ("I'm looking for…", "I'm not sure here…").
3. I'll try not to help, and you can stop at any time.

Ask the tester to close private apps (mail, chat) first, since screenpipe starts recording the screen once installed.

### Timing rules

- **Start**: the moment the tester opens `SETUP.md`.
- **End**: step 6 doctor prints `All required checks passed.`.
- Note the time at the end of each step and fill in the table below. Step 7 (trial run) is optional, timed separately, and not counted in the total.
- Note long download waits (over 1 minute) separately, so the report can say "X minutes of that were waiting for downloads".

### When to step in

- **Don't help proactively**: don't point at the screen or say "look further down".
- Step in only in two cases: **stuck for more than 3 minutes**, or the tester is **about to do something harmful** (e.g. deleting the wrong file).
- When stepping in, give the smallest hint possible (e.g. "have another look at the last paragraph of step 3"), and **log a help request**: write down the time, the step and what you said.
- **Don't edit the docs** during the test; note things down first.

### Log sheet

Time per step (minutes):

| Step 1 screenpipe | Step 2 AI key | Step 3 Node/Python | Step 4 install pipe | Step 5 wizard | Step 6 self-check | Total | Help requests |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

Observations (log hesitations, errors, help requests and long waits; the tester's exact words are especially useful):

| Time | Step | What happened | Type: hesitation / error / help / wait | Tester's words |
| --- | --- | --- | --- | --- |
| | | | | |

## 4. Post-test interview (5 minutes, ask in English)

1. *Which step was the hardest, and why?*
2. *Was anything in the instructions unclear or in the wrong order?*
3. **Privacy understanding check**: *In your own words, what does ChalkBack record, and what does it share with the school?*
   If they can't answer "recordings and screenshots never leave the computer; only approved coverage data is shared", the table at the top of SETUP needs fixing.
4. *From 1 to 5, how confident are you that you could do this again alone? Could a colleague teacher do it?*

Then help the tester **uninstall**: follow *Uninstall* in SETUP, then quit and uninstall screenpipe and delete `~/.screenpipe` and `~/.chalkback`.
Finally, revoke the test AI key and ask D to delete the test invite code and the test teacher account.

## 5. Sort issues and fix the docs

Put each observation into one of these categories:

| Category | Example | Who fixes |
| --- | --- | --- |
| Docs unclear | A sentence is hard to understand, can't find a button | B, fix right away |
| Missing step or wrong order | "Reopen the terminal" is missing, or B must be done before A | B, fix right away |
| Product issue | Wizard errors, doctor false alarm, pipe won't install | The relevant owner: C for the console, A for pipe permissions and data, D for the Hub. Report in the group chat with the time and a screenshot |
| Environment issue | Slow network, no admin rights on a work computer | Add a note to the FAQ |

Fix issues that **caused a help request or a stall of more than 3 minutes** first. After fixing:
1. Fill in this run's results in the *New-user test log* table at the end of `SETUP.md`;
2. If time allows, have a second tester run it again, or at least redo the changed steps yourself;
3. Commit: `git commit -m "TB7: newcomer test results, SETUP fixes"`.

## 6. Numbers for the demo and the pitch

**Report honestly**: use the measured total time, and mention any help requests. Judges may ask for details; numbers that hold up under questioning matter more than numbers that look good.

Phrasings you can use:

- No help requests: *"A first-time user who had never seen ChalkBack installed it in **X minutes** using only our SETUP guide."*
- With help requests: *"... in **X minutes** with **N** hint(s) — we fixed those steps in the guide afterwards."*

Send to:
- **D**: pitch slides;
- **A**: `docs/DEMO.md` and rehearsal;
- **B yourself**: the script for demo 0:15–0:35.

---

## Tester card (print or send this part)

**Thank you for helping us!**

We are testing our **installation guide**, not you. If something is confusing, that is exactly what we need to find out.

**What to do**

1. Open the guide: `docs/SETUP.md` in <https://github.com/wangunuxe/Chalkback>.
2. Follow it from the top, on your own, until step 6 says **All required checks passed**.
3. Please **think aloud** — say what you are looking for and what you are unsure about.
4. We will stay quiet and only step in if you are stuck for several minutes. You can stop at any time.

**You will receive:** an invite code and an AI key for this test (both are deleted afterwards).

**Privacy:** the guide installs *screenpipe*, which records your screen and microphone **on your laptop only**.
Please close private apps (mail, chat) before starting. Nothing is sent to us, and we will help you uninstall
everything at the end.

**Time:** about 30–40 minutes, plus a few questions at the end.
