<!-- 负责人：A（TA3）。由 pipe.md 第 3 步引用。 -->

# map_kp：把讲解片段对到考纲知识点

## 目标

判断本节课的每个讲解片段在讲考纲的哪个知识点，算出每个知识点讲了多少分钟，写成本机使用的 `$OUT/coverage.json`。
这份结果决定出题范围（只考讲过的点）、漏讲提醒和学校看板，所以**宁可漏标，不要错标**。

## 输入

1. `$OUT/segments.json`：片段数组，每段有 `segment_id`、`start`、`end`、`speech`（老师原话）、`slide_text`（屏幕上的课件文字）。
2. `$CB/cache/syllabus.json`：`syllabus_id`、`version`、`knowledge_points`（`kp_id`、`title`、`keywords`）。
3. `$WORK/lesson.json`（第 1 步 `current_lesson.py` 的输出）：`lesson_id`、`teacher_id`、`class_id`。
   这三个字段只从这里取，不要从片段或 `config.json` 推断。

## 判断规则

对每个片段，决定它在讲哪个知识点（0 个、1 个或最多 2 个）：

1. **以老师的话（`speech`）为准**：老师在解释、举例、纠错或带学生练习这个知识点，才算讲了。
   `slide_text` 只用来帮助理解老师在讲什么；只有课件上出现、老师没讲的内容不算。
2. **顺口提到不算**：只是一句话带过（“我们下次讲 imparfait”）、点名、课堂管理、闲聊，不对应任何知识点。
3. **最多 2 个**：一段同时在比较两个知识点（如对比 avoir 和 être 作助动词）时可以记 2 个；更多就选讲得最多的 2 个。
4. **只用考纲里的 `kp_id`**，不要发明新的知识点。
5. **拿不准时用关键词兜底**：老师原话里出现某知识点的标题，或至少 2 个不同的关键词，才记这个知识点；
   只出现 1 个关键词（如“accord”同时属于几个知识点）不记。

## 计算

- 片段时长 = `end` − `start`（分钟）。
- 一个片段记在 n 个知识点下时，每个知识点分到 时长 ÷ n。
- 每个知识点的 `minutes` = 分到的时长之和，保留 1 位小数。
- `covered` = `minutes` ≥ 1.0（讲不到 1 分钟不算讲过）。
- `segment_ids` = 记在这个知识点下的片段，按时间顺序；没有就是 `[]`，`minutes` 为 0。
- **考纲的每个知识点都列一次**，包括没讲的（`covered: false`）。
- `syllabus_id`、`syllabus_version` 取自 `syllabus.json` 的 `syllabus_id`、`version`；`generated_at` 为当前时间（ISO 8601，带时区偏移）。

## 输出

严格符合 `contracts/coverage.schema.json`，不要多写字段（不要写理由、原话或片段文字）：

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

## 检查

写完后依次运行，任何一个报错就按错误信息修改后重试（同一步最多 3 轮，见 pipe.md 硬约束）：

```bash
python $PIPE_DIR/scripts/validate.py coverage $OUT/coverage.json
python $PIPE_DIR/scripts/check_coverage.py --coverage $OUT/coverage.json --segments $OUT/segments.json \
    --syllabus $CB/cache/syllabus.json --lesson $WORK/lesson.json
```

`check_coverage.py` 会检查：片段 id 都存在、分钟数按上面的规则算对、`covered` 与分钟数一致、考纲和课程信息一致。
