<!-- 负责人：B（TB3）。由 pipe.md 第 7 步引用。 -->

# 出题：gen_quiz

你要为刚结束的这节课写一份课后小测验，学生下课后用手机作答。老师会先审核每一道题（审批 A2），
所以每道题都必须能追溯到课上老师说过的原话。

## 输入

| 文件 | 内容 |
| --- | --- |
| `$WORK/plan.json` | `plan_quiz.py` 的输出。`allocation` 规定每个知识点出几题，**必须严格照做** |
| `$OUT/coverage.json` | 本节课覆盖表。每个知识点的 `segment_ids` 是讲这个点的片段 |
| `$OUT/segments.json` | 片段：`speech` 是老师的转写原文，`slide_text` 是当时的课件文字，`evidence.frame_ids` 是截图 id |
| `$CB/cache/syllabus.json` | 考纲：知识点标题和关键词 |
| `$CB/state/style_profile.json` | 这位老师的出题风格（可能不存在） |

## 输出

写 `$OUT/quiz.json`，格式如下（契约 `quiz`，不得增删字段）：

```json
{"quiz_id": "Q-<lesson_id>", "lesson_id": "<lesson_id>", "class_id": "<class_id>", "status": "pending",
 "style_profile_version": <风格文件的 version；没有风格文件时为 0>,
 "questions": [
   {"q_id": "Q1", "kp_id": "KP03", "type": "mcq", "prompt": "…", "choices": ["…", "…", "…", "…"], "answer": 1,
    "time_limit_s": 20,
    "source": {"segment_id": "S-…-003", "quote": "<从 speech 原样复制的一句>", "frame_ids": [5531]}}
 ]}
```

- `type`：`mcq`（`answer` 是选项下标，从 0 开始）、`fill_blank`（`answer` 是字符串，不要 `choices`）、
  `true_false`（`answer` 是 `true` / `false`，不要 `choices`）。
- `q_id` 依次为 `Q1`、`Q2`……
- `time_limit_s` 默认：mcq 20，true_false 15，fill_blank 30。风格文件另有要求时照风格。

## 怎么写

1. **只考讲过的内容。** 每道题考的知识点和题数按 `allocation`。题目内容只能来自这节课讲这个知识点的片段
   （`coverage.json` 中该知识点的 `segment_ids`），不要考课上没讲的东西，即使考纲里有。
2. **先找原话，再出题。** 在片段的 `speech` 里选一句能支撑这道题的话，**逐字复制**到 `source.quote`
   （5–25 个词，连续的一段；标点可以不同，词不能改）。转写里没有合适原话的内容不要出题。
   `source.frame_ids` 从同一片段的 `evidence.frame_ids` 里选（不确定就全部放上），不要编 id。
3. **用课堂的语言出题**，和转写同一种语言。题干简短，手机一屏能看完。
4. **按老师的风格写。** 风格文件里每条 `rule` 都要体现，例如“偏好填空题”就多出填空题，
   “干扰项用学生常见错误”就用常见错误做干扰项。没有风格文件时：以 mcq 为主，至少一道 fill_blank 或 true_false。
5. **每种题型的要求：**
   - mcq：4 个选项，只有一个正确；干扰项要像真的（常见错误、相近形式），不要明显离谱或互相重复；正确答案的位置要变化。
   - fill_blank：题干里用 `___` 标出唯一的空；答案是一个词或很短的词组，**只有一种正确写法**（判分忽略大小写和多余空格，
     但不忽略重音和拼写）；题干不能直接透露答案。
   - true_false：陈述要么明确对、要么明确错，不要“部分正确”；错的陈述用学生容易犯的错误。
6. 题目之间不要重复考同一句话。

## 自检（必须做）

依次运行，任何一步失败都按错误信息修改 `quiz.json` 后重跑，最多 3 轮：

```bash
python $PIPE_DIR/scripts/validate.py quiz $OUT/quiz.json
python $PIPE_DIR/scripts/check_quiz.py --quiz $OUT/quiz.json --segments $OUT/segments.json \
  --coverage $OUT/coverage.json --plan $WORK/plan.json
```

`check_quiz.py` 报“quote 找不到”时，重新从 `speech` 原样复制，不要改写原话去迁就题目。

## 规则

- `status` 必须是 `pending`：没有老师审核就不会发布。
- 不要发明契约之外的字段。
- 原话和 screenpipe id 只写在本机的 `quiz.json` 里；学生页面由 `build_game.py` 生成，它会去掉这些内容。
