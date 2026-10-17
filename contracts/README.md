# contracts/

Shared by everyone. **Frozen Saturday 13:00 (H1)**; after that, changes need unanimous agreement from all four teammates and must update the schema, `examples/` and design doc §5 / §6 together.

| Contract | schema | Example | Producer → consumer | Can it leave the teacher's computer |
| --- | --- | --- | --- | --- |
| syllabus | `syllabus.schema.json` | `examples/syllabus.json` | D → A, B, C | Already on the Hub |
| lesson_plan | `lesson_plan.schema.json` | `examples/lesson_plan.json` | C → B | No |
| segment | `segment.schema.json` | `examples/segment.json` | A → B (`segments.json` is an array) | No |
| coverage | `coverage.schema.json` | `examples/coverage.json` | A → B, C | Only as coverage_share |
| coverage_share | `coverage_share.schema.json` | `examples/coverage_share.json` | C → Hub | **The only coverage format that can be uploaded** |
| quiz | `quiz.schema.json` | `examples/quiz.json` | B → C | No |
| alerts | `alerts.schema.json` | `examples/alerts.json` | B → C | No |
| style_profile | `style_profile.schema.json` | `examples/style_profile.json` | B → B | No |
| edit_event | `edit_event.schema.json` | `examples/edit_event.json` | C → B (one per line in `edits.jsonl`) | No |
| weights | `weights.schema.json` | `examples/weights.json` | C → B | No |
| attempt | `attempt.schema.json` | `examples/attempt.json` | Game → C (one per line in `attempts.jsonl`) | No |
| kp_stats | `kp_stats.schema.json` | `examples/kp_stats.json` | C → C | No |
| audit_event | `audit_event.schema.json` | `examples/audit_event.json` | D | Already on the Hub |
| config | `config.schema.json` | `examples/config.json` | C → B (§6.2) | No (contains the token) |

The example content (French grammar, 4A, T1) is only a placeholder; A + D replace it once the demo topic is decided (H4).

Validation:

```bash
python pipe/scripts/validate.py coverage path/to/coverage.json   # single file; .jsonl / arrays validated item by item
python pipe/scripts/validate.py --examples                       # all examples
```

`pipe/` is installed as a standalone directory, and the teacher's computer won't have this `contracts/`, so the schemas are copied to `pipe/schemas/`.
After changing a schema here, run `make sync-schemas`; `make check` verifies the two copies match.

## Conventions

- Time: ISO 8601, timezone offset required (`2026-10-17T10:12:05+02:00`), enforced by a regex in the schema.
- `lesson_id` = `L-{teacher_id}-{YYYYMMDD}-{HHMM}`; `segment_id` = `S-{lesson_id}-{NNN}`; `quiz_id` = `Q-{lesson_id}`.
- Every object has `additionalProperties: false`: even one extra field is a violation, which keeps raw transcripts or screenpipe ids out of uploaded data.
- In the `weights` example, KP03 = 2.5: accuracy < 50% (2.0) + Kahoot weak point (+0.5).
