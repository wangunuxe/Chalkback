<!-- Owner: B (TB5). Referenced by step 6 of pipe.md. -->

# Learn the teacher's style: learn_style

The same pipe is distributed to the whole school, but each teacher's agent must learn **that teacher's own** question-writing style: from their past screens on quiz platforms,
and from how they edit your questions in the console. The style profile is shown to the teacher (console `/style`) and is also what `gen_quiz.md` writes questions from,
so every rule must be concrete, actionable, and backed by evidence.

## Input: `$WORK/style_inputs.json` (output of `style_inputs.py`)

| Field | Content |
| --- | --- |
| `current_profile` | The current style profile, or `null` if there is none |
| `next_version`, `now` | The new file's `version` and `updated_at`; **use them verbatim** |
| `screen_history` | Screen text from the teacher's Kahoot / Quizlet / Forms windows; each frame has `frame_id`, `timestamp`, `platform`, `text` |
| `edits` | New records of the teacher reviewing questions in the console. `action`: `edit` (`changed` lists the changed fields, `before` / `after` are the full questions), `approve`, `reject`, `delete` |

## Output

Write to **`$WORK/style_profile.json`** (do not overwrite `$CB/state/` yet), in this format (contract `style_profile`):

```json
{"teacher_id": "<teacher_id>", "version": <next_version>, "updated_at": "<now>",
 "rules": [
   {"rule": "Privilégier les questions à trous", "origin": "screen_history", "evidence": {"frame_ids": [4410], "timestamp": "<timestamp of one of those frames>"}},
   {"rule": "Distracteurs : erreurs fréquentes des élèves (accords oubliés)", "origin": "teacher_edit", "evidence": {"edit_ids": ["E3"]}}
 ]}
```

## What to look at

In the screen text, look at the questions **the teacher wrote themselves** (question editor, question list, preview page), paying attention to:

- **Question type preference**: the share of multiple choice, fill-in-the-blank, and true/false;
- **Choices**: how many choices; whether distractors are common mistakes, look-alike words, or obviously wrong;
- **Question stem**: length; whether it uses full example sentences or a scenario; whether students are addressed as tu or vous; formal or casual tone;
- **Difficulty and time limit**: how many seconds per question;
- **Other clear habits**: e.g. every question tests one concrete example sentence, or the correct answer is always placed in different positions.

In `edits`, look at **what the teacher was unhappy with** in your questions:
- `edit`: compare the `changed` fields between `before` and `after`. For example, the teacher replaced distractors with common mistakes, shortened the stem, or changed multiple choice to fill-in-the-blank;
  each of these is evidence for a rule. **Rules may only come from fields listed in `changed`**: what the teacher did not change (e.g. 4 choices both before and after)
  must not be taken as this teacher's preference; that is just how you originally wrote it.
- `reject` / `delete`: the teacher doesn't want this kind of question; write it as an "Avoid …" rule.
- `approve`: questions the teacher accepted; they can corroborate existing rules, but do not invent a new rule from approvals alone.

## How to write rules

1. **Concrete and actionable**: write "distractors use common student spelling or agreement mistakes", not "high-quality questions".
2. **Every rule has evidence**:
   - `origin: "screen_history"`: `frame_ids` lists the frames supporting it, and `timestamp` is copied verbatim from the `timestamp` of one of those frames;
   - `origin: "teacher_edit"`: `edit_ids` lists the edit records supporting it.
   When a rule is supported by both kinds of evidence, choose the stronger one. **Do not write a rule you cannot find evidence for.**
3. **Update on top of the old file**: keep rules from `current_profile` that still hold (together with their original evidence); rewrite or delete rules overturned by new edits;
   add newly discovered rules. The teacher's own edits (`teacher_edit`) weigh more than screen history; when the two conflict, follow the edits.
4. **3–8 rules**, no duplicates, no contradictions. One short sentence each, in the same language as the lesson.
5. Do not copy student information into rules, and do not copy whole question texts; when an example is needed, give just one short word.

## Self-check (mandatory)

```bash
python $PIPE_DIR/scripts/validate.py style_profile $WORK/style_profile.json
python $PIPE_DIR/scripts/check_style.py --profile $WORK/style_profile.json --inputs $WORK/style_inputs.json
```

If either fails, fix according to the error messages and rerun, at most 3 rounds. Once both pass, copy `$WORK/style_profile.json` to `$CB/state/style_profile.json`.
Still failing after 3 rounds: **do not** overwrite the old file; this step counts as failed but does not affect quiz generation (the old style profile is kept).
