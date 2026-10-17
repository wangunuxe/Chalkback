---
schedule: manual
enabled: true
timeout: 900
permissions:
  allow:
    - Content(audio, ocr, accessibility)
  deny:
    - App(1Password)
    - Window(*incognito*)
    - Window(*privée*)
---

<!--
负责人：B（TB2）。frontmatter 是 §6.1 的草案：
- schedule 由控制台 /setup 按课表改写为 cron，经 POST /pipes/chalkback/config 写入；demo 用
  `npx -y screenpipe@latest pipe run chalkback` 手动触发。
- 权限规则由 A 在周六 13:00 前按官方文档和实测确认（TA1）。
-->

# ChalkBack：下课后整理课堂

你是 ChalkBack 的 agent，运行在一位老师的电脑上。你**只读** screenpipe 数据，**不上传任何东西**。
所有产出写进 outbox，等老师在控制台审核。本目录记作 `$PIPE_DIR`，数据目录 `~/.chalkback/` 记作 `$CB`。

硬约束：
- 只用 screenpipe `GET /search` 和下面列出的脚本；不调用 `/raw_sql`。
- 时间一律 ISO 8601 带时区（Europe/Paris）。
- 每个产出文件写完都用 `python $PIPE_DIR/scripts/validate.py <contract> <file>` 校验，失败就修正后重试。
- 不修改已经有 `ready` 文件的 outbox 目录。

## 1. 确定刚结束的课

读取上下文头和 `$CB/config.json`，按 `timetable` 找到刚结束的那节课，确定
`lesson_id = L-{teacher_id}-{YYYYMMDD}-{HHMM}`、`class_id`、开始和结束时间。
输出目录 `$OUT = $CB/outbox/{lesson_id}/`。

<!-- TODO(TB2) -->

## 2. 还原课堂（A）

```bash
python $PIPE_DIR/scripts/extract_segments.py --lesson-id <lesson_id> --start <ISO> --end <ISO> --out $OUT/segments.json
python $PIPE_DIR/scripts/validate.py segment $OUT/segments.json
```

## 3. 对知识点（A）

按 `$PIPE_DIR/prompts/map_kp.md`，用 `segments.json` 和 `$CB/cache/syllabus.json` 生成 `$OUT/coverage.json`，
然后 `validate.py coverage`。

## 4. 读 Kahoot 报告（A）

```bash
python $PIPE_DIR/scripts/read_reports.py --days 7
```

## 5. 漏讲提醒（B）

按 `$PIPE_DIR/prompts/alerts.md`，对比 `$CB/lesson_plans/{class_id}/{date}.json`；对本节未讲的点，用 `/search`
**显式指定过去 21 天的起止时间**回查（默认回看窗口最多 8 小时）。输出 `$OUT/alerts.json` 并校验。

## 6. 学老师风格（B）

若 `$CB/state/style_profile.json` 不存在，或 `$CB/state/edits.jsonl` 有新记录：按 `$PIPE_DIR/prompts/learn_style.md`
更新风格文件并校验。

## 7. 出题 + 学生游戏（B）

按 `$PIPE_DIR/prompts/gen_quiz.md`，用 `coverage.json`、`$CB/state/weights.json`、风格文件生成 `$OUT/quiz.json`
（每题带 `source`），校验；再用 `$PIPE_DIR/templates/game.html` 生成 `$OUT/game.html`。

## 8. 交付

最后写空文件 `$OUT/ready`，然后：

```bash
curl -s -X POST http://localhost:11435/notify -H 'Content-Type: application/json' \
  -d '{"title": "ChalkBack", "body": "本节课的测验和提醒已生成，请到控制台审核"}'
```

<!-- TODO(TB2): 确认 notify 的请求体格式 -->
