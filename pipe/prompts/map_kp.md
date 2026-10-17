<!-- Owner: A (TA3). Referenced by step 3 of pipe.md. -->

# map_kp: map teaching segments to syllabus knowledge points

## Goal

Decide which syllabus knowledge point each teaching segment of this lesson covers, compute how many minutes each knowledge point was taught, and write the result to the local `$OUT/coverage.json`.
This result determines the quiz scope (only points that were taught are tested), the missed-point alerts and the school dashboard, so **better to leave a segment unlabelled than to label it wrongly**.

## Input

1. `$OUT/segments.json`: array of segments, each with `segment_id`, `start`, `end`, `speech` (the teacher's own words), `slide_text` (slide text on the screen).
2. `$CB/cache/syllabus.json`: `syllabus_id`, `version`, `knowledge_points` (`kp_id`, `title`, `keywords`).
3. `$WORK/lesson.json` (output of `current_lesson.py` in step 1): `lesson_id`, `teacher_id`, `class_id`.
   Take these three fields only from here; do not infer them from the segments or from `config.json`.

## Decision rules

For each segment, decide which knowledge points it teaches (0, 1, or at most 2):

1. **The teacher's words (`speech`) are what count**: a knowledge point is taught only if the teacher is explaining it, giving examples, correcting mistakes, or practising it with students.
   `slide_text` only helps you understand what the teacher is talking about; content that appears only on the slides and that the teacher does not talk about does not count.
2. **Passing mentions don't count**: a one-line mention ("we'll do the imparfait next time"), roll call, classroom management, or small talk maps to no knowledge point.
3. **At most 2**: a segment that compares two knowledge points at once (e.g. contrasting avoir and être as auxiliaries) may get 2; if more, pick the 2 taught the most.
4. **Use only `kp_id`s from the syllabus**; do not invent new knowledge points.
5. **When unsure, fall back on keywords**: assign a knowledge point only if the teacher's words contain its title or at least 2 different keywords;
   a single keyword (e.g. "accord", which belongs to several knowledge points) is not enough.

## Computation

- Segment duration = `end` − `start` (minutes).
- When a segment is assigned to n knowledge points, each one gets duration ÷ n.
- Each knowledge point's `minutes` = sum of its shares, rounded to 1 decimal place.
- `covered` = `minutes` ≥ 1.0 (less than 1 minute does not count as taught).
- `segment_ids` = the segments assigned to this knowledge point, in chronological order; `[]` if none, with `minutes` 0.
- **List every knowledge point in the syllabus exactly once**, including those not taught (`covered: false`).
- `syllabus_id` and `syllabus_version` come from `syllabus_id` and `version` in `syllabus.json`; `generated_at` is the current time (ISO 8601, with timezone offset).

## Output

Must strictly conform to `contracts/coverage.schema.json`; do not write extra fields (no reasons, quotes, or segment text):

```json
{
  "lesson_id": "L-T1-20261017-1000",
  "teacher_id": "T1",
  "class_id": "4A",
  "syllabus_id": "fr-grammaire-4e",
  "syllabus_version": 1,
  "generated_at": "2026-10-17T11:05:00+02:00",
  "points": [
    {"kp_id": "KP01", "covered": true, "minutes": 4.5, "segment_ids": ["S-L-T1-20261017-1000-001"]},
    {"kp_id": "KP02", "covered": false, "minutes": 0, "segment_ids": []},
    {"kp_id": "KP03", "covered": true, "minutes": 6.0, "segment_ids": ["S-L-T1-20261017-1000-002"]},
    {"kp_id": "KP04", "covered": false, "minutes": 0, "segment_ids": []}
  ]
}
```

## Checks

After writing, run these in order; if any reports an error, fix according to the error messages and retry (at most 3 rounds per step, see the hard rules in pipe.md):

```bash
python $PIPE_DIR/scripts/validate.py coverage $OUT/coverage.json
python $PIPE_DIR/scripts/check_coverage.py --coverage $OUT/coverage.json --segments $OUT/segments.json \
    --syllabus $CB/cache/syllabus.json --lesson $WORK/lesson.json
```

`check_coverage.py` checks that: all segment ids exist, minutes are computed according to the rules above, `covered` is consistent with the minutes, and the syllabus and lesson information match.
