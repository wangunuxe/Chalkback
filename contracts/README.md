# contracts/

全员共有。**周六 13:00（H1）冻结**，之后改动需四位队员一致同意，并同时更新 schema、`examples/` 和技术文档 §5 / §6。

| 契约 | schema | 示例 | 产生方 → 使用方 | 能否离开老师电脑 |
| --- | --- | --- | --- | --- |
| syllabus | `syllabus.schema.json` | `examples/syllabus.json` | D → A、B、C | 本来就在 Hub |
| lesson_plan | `lesson_plan.schema.json` | `examples/lesson_plan.json` | C → B | 否 |
| segment | `segment.schema.json` | `examples/segment.json` | A → B（`segments.json` 是数组） | 否 |
| coverage | `coverage.schema.json` | `examples/coverage.json` | A → B、C | 只能以 coverage_share 形式 |
| coverage_share | `coverage_share.schema.json` | `examples/coverage_share.json` | C → Hub | **唯一可上传的覆盖格式** |
| quiz | `quiz.schema.json` | `examples/quiz.json` | B → C | 否 |
| alerts | `alerts.schema.json` | `examples/alerts.json` | B → C | 否 |
| style_profile | `style_profile.schema.json` | `examples/style_profile.json` | B → B | 否 |
| edit_event | `edit_event.schema.json` | `examples/edit_event.json` | C → B（`edits.jsonl` 每行一条） | 否 |
| weights | `weights.schema.json` | `examples/weights.json` | C → B | 否 |
| attempt | `attempt.schema.json` | `examples/attempt.json` | 游戏 → C（`attempts.jsonl` 每行一条） | 否 |
| kp_stats | `kp_stats.schema.json` | `examples/kp_stats.json` | C → C | 否 |
| audit_event | `audit_event.schema.json` | `examples/audit_event.json` | D | 本来就在 Hub |
| config | `config.schema.json` | `examples/config.json` | C → B（§6.2） | 否（含 token） |

示例内容（法语语法、4A、T1）只是占位，演示主题定下后由 A + D 替换（H4）。

校验：

```bash
python pipe/scripts/validate.py coverage path/to/coverage.json   # 单个文件；.jsonl / 数组逐条校验
python pipe/scripts/validate.py --examples                       # 全部示例
```

`pipe/` 是独立安装的目录，装到老师电脑上时没有这里的 `contracts/`，所以 schema 会复制一份到 `pipe/schemas/`。
改了这里的 schema 后运行 `make sync-schemas`；`make check` 会检查两份是否一致。

## 约定

- 时间：ISO 8601，必须带时区偏移（`2026-10-17T10:12:05+02:00`），schema 用正则强制。
- `lesson_id` = `L-{teacher_id}-{YYYYMMDD}-{HHMM}`；`segment_id` = `S-{lesson_id}-{NNN}`；`quiz_id` = `Q-{lesson_id}`。
- 所有对象 `additionalProperties: false`：多一个字段也算违约，防止原文或 screenpipe id 混进上传数据。
- `weights` 示例里 KP03 = 2.5：正确率 < 50%（2.0）+ Kahoot 薄弱点（+0.5）。
