<!-- Owner: B (TB3). Referenced by step 7 of pipe.md. -->

# Quiz generation: gen_quiz

You are writing a short post-lesson quiz for the lesson that just ended; students answer it in a browser on the teacher's computer (no mobile version). The teacher reviews every question first (approval A2),
so every question must be traceable to a quote the teacher actually said in class.

## Input

| File | Content |
| --- | --- |
| `$WORK/plan.json` | Output of `plan_quiz.py`. `allocation` sets how many questions each knowledge point gets; **follow it exactly** |
| `$OUT/coverage.json` | This lesson's coverage table. Each knowledge point's `segment_ids` are the segments that teach it |
| `$OUT/segments.json` | Segments: `speech` is the teacher's verbatim transcript, `slide_text` is the slide text at the time, `evidence.frame_ids` are screenshot ids |
| `$CB/cache/syllabus.json` | Syllabus: knowledge point titles and keywords |
| `$CB/state/style_profile.json` | This teacher's question-writing style (may not exist) |

## Output

Write `$OUT/quiz.json` in the following format (contract `quiz`; do not add or remove fields):

```json
{"quiz_id": "Q-<lesson_id>", "lesson_id": "<lesson_id>", "class_id": "<class_id>", "status": "pending",
 "style_profile_version": <the style profile's version; 0 when there is no style profile>,
 "questions": [
   {"q_id": "Q1", "kp_id": "KP03", "type": "mcq", "prompt": "…", "choices": ["…", "…", "…", "…"], "answer": 1,
    "time_limit_s": 20,
    "source": {"segment_id": "S-…-003", "quote": "<one sentence copied verbatim from speech>", "frame_ids": [5531]}}
 ]}
```

- `type`: `mcq` (`answer` is the choice index, starting from 0), `fill_blank` (`answer` is a string; no `choices`),
  `true_false` (`answer` is `true` / `false`; no `choices`).
- `q_id` runs `Q1`, `Q2`, … in order.
- `time_limit_s` defaults: mcq 20, true_false 15, fill_blank 30. If the style profile says otherwise, follow the style.

## How to write it

1. **Only test what was taught.** The knowledge point and number of questions follow `allocation`. Question content may only come from the segments of this lesson that teach that knowledge point
   (that knowledge point's `segment_ids` in `coverage.json`); do not test anything not taught in class, even if it is in the syllabus.
2. **Find the quote first, then write the question.** Pick a sentence in a segment's `speech` that supports the question and **copy it word for word** into `source.quote`
   (5–25 words, one contiguous stretch; punctuation may differ, words may not be changed). Do not write questions on content that has no suitable quote in the transcript.
   The quote must **support the question on its own**: the teacher looks only at this sentence during review, so quote the rule together with its conditions,
   and do not cut off conditions like "only when …" or "unless …" (e.g. quote "s'accorde avec le COD seulement quand il est placé
   avant le verbe", not just "s'accorde avec le COD seulement").
   Choose `source.frame_ids` from the same segment's `evidence.frame_ids` (if unsure, include them all); do not make up ids.
3. **Write in the language of the lesson**, the same language as the transcript. Keep the question stem short, readable on one screen without scrolling.
4. **Write in the teacher's style.** Every `rule` in the style profile must be reflected, e.g. "prefers fill-in-the-blank" means more fill-in-the-blank questions,
   "distractors use common student mistakes" means using common mistakes as distractors. With no style profile: mostly mcq, with at least one fill_blank or true_false.
5. **Requirements per question type:**
   - mcq: 4 choices, exactly one correct; distractors must be plausible (common mistakes, similar forms), not obviously absurd or duplicating each other; vary the position of the correct answer.
   - fill_blank: mark the single blank in the stem with `___`; the answer is one word or a very short phrase with **only one correct spelling** (grading ignores case and extra spaces,
     but not accents or spelling); the stem must not give away the answer.
   - true_false: the statement must be clearly true or clearly false, never "partly true"; false statements should use mistakes students commonly make.
6. **Questions should test different content and cite different quotes where possible.** But if the knowledge point was only taught in a sentence or two and there aren't enough quotes to go round,
   let several questions **cite the same complete quote** and vary the questions themselves (different example words, positive and negative cases, different question types);
   **do not split one sentence into pieces just to avoid repetition**.

## Self-check (mandatory)

Run these in order; if any fails, fix `quiz.json` according to the error messages and rerun, at most 3 rounds:

```bash
python $PIPE_DIR/scripts/validate.py quiz $OUT/quiz.json
python $PIPE_DIR/scripts/check_quiz.py --quiz $OUT/quiz.json --segments $OUT/segments.json \
  --coverage $OUT/coverage.json --plan $WORK/plan.json
```

When `check_quiz.py` reports that a `source.quote` cannot be found in the segment's transcript, copy it again verbatim from `speech`; do not rewrite the quote to fit the question.

## Rules

- `status` must be `pending`: nothing is published without the teacher's review.
- Do not invent fields outside the contract.
- Quotes and screenpipe ids are written only in the local `quiz.json`; the student page is generated by `build_game.py`, which strips them out.
