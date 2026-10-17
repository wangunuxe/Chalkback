<!-- 负责人：A（TA3）。由 pipe.md 引用。 -->

# map_kp

## 目标

把讲解片段（`segments.json`）精确对照考纲（`cache/syllabus.json`），识别本节课讲授了哪些知识点，计算覆盖时长与关联证据，生成本机使用的 `coverage.json`。

## 输入

1. `segments.json`：`outbox/{lesson_id}/segments.json`（包含片段起止时间、`speech`、`slide_text` 与 `evidence`）。
2. `cache/syllabus.json`：`~/.chalkback/cache/syllabus.json`（包含当前生效的考纲 `syllabus_id`、`version` 与知识点清单 `knowledge_points`）。
3. 课程元数据（从 `segments[0].lesson_id` 或 `~/.chalkback/config.json` 取得 `lesson_id`、`teacher_id`、`class_id`）。

## 输出

严格符合 `contracts/coverage.schema.json` 的 JSON 对象，须能通过 `python pipe/scripts/validate.py coverage <path>` 校验。

```json
{
  "lesson_id": "L-T1-20261017-1000",
  "teacher_id": "T1",
  "class_id": "4A",
  "syllabus_id": "fr-grammaire-4e",
  "syllabus_version": 1,
  "generated_at": "2026-10-17T11:05:00+02:00",
  "points": [
    {
      "kp_id": "KP01",
      "covered": true,
      "minutes": 4.5,
      "segment_ids": ["S-L-T1-20261017-1000-001", "S-L-T1-20261017-1000-002"]
    },
    {
      "kp_id": "KP02",
      "covered": false,
      "minutes": 0.0,
      "segment_ids": []
    }
  ]
}