<!-- 负责人：B（TB4）。由 pipe.md 第 5 步引用。 -->

# 漏讲提醒：alerts

你要告诉老师：教案里计划讲、但这节课没讲到的知识点，哪些是**真的还没讲**（需要补），
哪些其实**以前已经讲过**（不用担心）。误报会让老师不再相信提醒，所以拿不准时要说明原因，而不是瞎猜。

## 输入

| 文件 | 内容 |
| --- | --- |
| `$WORK/lookback.json` | `lookback.py` 的输出。`candidates` 就是“教案计划讲、本节没讲”的知识点，每个带回查证据 |
| `$WORK/reports.json` | `read_reports.py` 的输出：Kahoot 报告里的薄弱知识点（可能是空数组） |

每个 candidate 的证据：
- `from_outbox`：过去 21 天里，这个班已经处理过的某节课的覆盖表记录它讲过。**这是可靠证据。**
- `search_hits`：用考纲关键词在 screenpipe 里搜到的片段。`content_type` 为 `audio` 是老师麦克风说的话，
  `ocr` 是屏幕上的文字；`in_class_slot` 表示是否在这个班的上课时段内。**只是候选。**
- `search_error`：回查失败的原因（例如 screenpipe 不可用）。

## 输出

写 `$OUT/alerts.json`（契约 `alerts`，不得增删字段）：

```json
{"lesson_id": "<lesson_id>",
 "missed": [{"kp_id": "KP02", "note": "<给老师看的一句话>"}],
 "covered_before": [{"kp_id": "KP01", "last_covered_at": "<证据里的时间，原样复制>"}],
 "weak_from_reports": [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "…"}]}
```

## 怎么判断

对 `candidates` 里的**每一个**知识点，必须放进 `missed` 或 `covered_before` 之一，不能遗漏也不能两边都放：

1. **有 `from_outbox`** → `covered_before`，`last_covered_at` 原样复制 `from_outbox.last_covered_at`。
2. **没有 `from_outbox`，看 `search_hits`**。只有同时满足下面几条，才算以前讲过 → `covered_before`，
   `last_covered_at` 原样复制**最近一条**满足条件的 hit 的 `timestamp`：
   - 是 `audio`（老师说的话），并且 `in_class_slot` 为 `true`；
   - 内容确实是在**讲解**这个知识点（解释规则、举例、纠错），而不是顺口提到关键词、布置作业或预告“下次讲”。
   只有 `ocr` 命中（例如在备课、改课件），或者命中在上课时段以外，都**不算**讲过。
3. **其余情况** → `missed`。`note` 写一句给老师看的话，用和课堂相同的语言，说清依据，例如：
   - 没有任何证据：“Prévu au plan de cours, non abordé aujourd'hui ni dans les 21 derniers jours.”
   - 只有不算数的命中：“Mentionné le 14/10 hors cours (diapositives), mais pas expliqué en classe.”
   - 有 `search_error`：“Non abordé aujourd'hui ; vérification des 21 derniers jours impossible.”

`lookback.json` 的 `has_lesson_plan` 为 `false`（老师没填教案）时，`candidates` 为空，`missed` 和 `covered_before` 都写空数组。

## weak_from_reports

原样复制 `$WORK/reports.json` 里的条目，去掉重复的。不要自己添加。

## 自检（必须做）

```bash
python $PIPE_DIR/scripts/validate.py alerts $OUT/alerts.json
python $PIPE_DIR/scripts/check_alerts.py --alerts $OUT/alerts.json --lookback $WORK/lookback.json --reports $WORK/reports.json
```

失败就按错误信息修改后重跑，最多 3 轮。`check_alerts.py` 报“不对应任何回查证据”时，说明你写的时间不是从证据里复制的。

## 规则

- 不要发明契约之外的字段。
- `note` 里不要引用课上原话，也不要写 screenpipe id，只写结论和日期。
