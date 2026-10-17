<!-- Owner: B (TB4). Referenced by step 5 of pipe.md. -->

# Missed-point alerts: alerts

You need to tell the teacher which knowledge points the lesson plan scheduled but this lesson did not cover are **really not covered yet** (need to be made up),
and which were in fact **already covered earlier** (nothing to worry about). False alarms make teachers stop trusting the alerts, so when unsure, state the reason instead of guessing.

## Input

| File | Content |
| --- | --- |
| `$WORK/lookback.json` | Output of `lookback.py`. `candidates` are the knowledge points "scheduled in the lesson plan but not covered in this lesson", each with look-back evidence |
| `$WORK/reports.json` | Output of `read_reports.py`: weak knowledge points from Kahoot reports (may be an empty array) |

Evidence for each candidate:
- `from_outbox`: within the past 21 days, the coverage table of an already-processed lesson of this class records it as covered. **This is reliable evidence.**
- `search_hits`: segments found in screenpipe by searching the syllabus keywords. `content_type` `audio` is what the teacher said into the microphone,
  `ocr` is text on the screen; `in_class_slot` says whether it falls within this class's timetabled slot. **Only candidates.**
- `search_error`: why the look-back failed (e.g. screenpipe unavailable).

## Output

Write `$OUT/alerts.json` (contract `alerts`; do not add or remove fields):

```json
{"lesson_id": "<lesson_id>",
 "missed": [{"kp_id": "KP02", "note": "<one sentence for the teacher>"}],
 "covered_before": [{"kp_id": "KP01", "last_covered_at": "<time from the evidence, copied verbatim>"}],
 "weak_from_reports": [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "…"}]}
```

## How to decide

**Every** knowledge point in `candidates` must go into exactly one of `missed` or `covered_before`: none may be left out, and none may go in both:

1. **Has `from_outbox`** → `covered_before`, with `last_covered_at` copied verbatim from `from_outbox.last_covered_at`.
2. **No `from_outbox`: look at `search_hits`**. It counts as covered earlier → `covered_before` only if all of the following hold,
   with `last_covered_at` copied verbatim from the `timestamp` of the **most recent** qualifying hit:
   - it is `audio` (the teacher speaking), and `in_class_slot` is `true`;
   - the content really is **teaching** this knowledge point (explaining the rule, giving examples, correcting mistakes), not a passing mention of a keyword, setting homework, or announcing "we'll cover it next time".
   Hits that are only `ocr` (e.g. preparing the lesson, editing slides), or hits outside the class slot, do **not** count as covered.
3. **Everything else** → `missed`. `note` is one sentence for the teacher, in the same language as the lesson, stating the basis, e.g.:
   - No evidence at all: "Prévu au plan de cours, non abordé aujourd'hui ni dans les 21 derniers jours."
   - Only hits that don't count: "Mentionné le 14/10 hors cours (diapositives), mais pas expliqué en classe."
   - Has `search_error`: "Non abordé aujourd'hui ; vérification des 21 derniers jours impossible."

When `has_lesson_plan` in `lookback.json` is `false` (the teacher has not filled in a lesson plan), `candidates` is empty, and both `missed` and `covered_before` are written as empty arrays.

## weak_from_reports

Copy the entries from `$WORK/reports.json` verbatim, removing duplicates. Do not add any of your own.

## Self-check (mandatory)

```bash
python $PIPE_DIR/scripts/validate.py alerts $OUT/alerts.json
python $PIPE_DIR/scripts/check_alerts.py --alerts $OUT/alerts.json --lookback $WORK/lookback.json --reports $WORK/reports.json
```

If either fails, fix according to the error messages and rerun, at most 3 rounds. When `check_alerts.py` reports that a `last_covered_at` does not match any look-back evidence, the time you wrote was not copied from the evidence.

## Rules

- Do not invent fields outside the contract.
- In `note`, do not quote the teacher's words from class and do not write screenpipe ids; write only the conclusion and dates.
