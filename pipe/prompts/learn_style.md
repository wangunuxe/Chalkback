<!-- 负责人：B（TB5）。由 pipe.md 第 6 步引用。 -->

# 学老师风格：learn_style

同一份 pipe 分发给全校，但每位老师的 agent 要学到**这位老师自己的**出题风格：从他过去在出题平台上的画面，
以及他在控制台里怎么修改你出的题。风格文件会显示给老师看（控制台 `/style`），也是 `gen_quiz.md` 出题的依据，
所以每条规则都要具体、能照着执行，并且有证据。

## 输入：`$WORK/style_inputs.json`（`style_inputs.py` 的输出）

| 字段 | 内容 |
| --- | --- |
| `current_profile` | 现在的风格文件，没有时为 `null` |
| `next_version`、`now` | 新文件的 `version` 和 `updated_at`，**原样使用** |
| `screen_history` | 老师在 Kahoot / Quizlet / Forms 窗口里的屏幕文字，每帧有 `frame_id`、`timestamp`、`platform`、`text` |
| `edits` | 老师在控制台审核题目的新记录。`action`：`edit`（`changed` 列出改了的字段，`before` / `after` 是完整题目）、`approve`、`reject`、`delete` |

## 输出

写到 **`$WORK/style_profile.json`**（先不要覆盖 `$CB/state/`），格式（契约 `style_profile`）：

```json
{"teacher_id": "<teacher_id>", "version": <next_version>, "updated_at": "<now>",
 "rules": [
   {"rule": "Privilégier les questions à trous", "origin": "screen_history", "evidence": {"frame_ids": [4410], "timestamp": "<其中一帧的 timestamp>"}},
   {"rule": "Distracteurs : erreurs fréquentes des élèves (accords oubliés)", "origin": "teacher_edit", "evidence": {"edit_ids": ["E3"]}}
 ]}
```

## 看什么

从屏幕文字里看老师**自己出的题**（编辑题目、题目列表、预览页），注意这些方面：

- **题型偏好**：多选、填空、判断各占多少；
- **选项**：几个选项；干扰项是常见错误、形近词，还是明显错误；
- **题干**：长短，用不用完整例句或情境，称呼学生用 tu 还是 vous，语气正式还是轻松；
- **难度和时限**：每题给多少秒；
- **其他明显习惯**：例如每题都考一个具体例句，或者总把正确答案放在不同位置。

从 `edits` 里看老师对你出的题**不满意什么**：
- `edit`：比较 `before` 和 `after` 的 `changed` 字段。例如老师把干扰项换成了常见错误、缩短了题干、把多选改成了填空，
  每一种都是一条规则的证据。
- `reject` / `delete`：这类题老师不要，写成“避免……”规则。
- `approve`：老师接受的题，可以佐证已有规则，但不要单凭 approve 发明新规则。

## 怎么写规则

1. **具体、可执行**：写“每道多选题 4 个选项，干扰项用学生常见的拼写或配合错误”，不要写“题目质量高”。
2. **每条规则都有证据**：
   - `origin: "screen_history"`：`frame_ids` 列出支撑它的帧，`timestamp` 原样复制其中一帧的 `timestamp`；
   - `origin: "teacher_edit"`：`edit_ids` 列出支撑它的修改记录。
   同时来自两种证据时，选更有力的那种。**找不到证据的规则不要写。**
3. **在旧文件基础上更新**：`current_profile` 里仍然成立的规则保留（连同原来的证据）；被新修改推翻的规则改写或删掉；
   新发现的规则加上。老师亲手修改（`teacher_edit`）的分量比屏幕历史大，两者冲突时听修改的。
4. **3–8 条**，不要重复，不要互相矛盾。用简短的一句话，语言与课堂相同。
5. 规则里不要抄学生信息，也不要整段照抄题目原文；需要举例时只举一个短词。

## 自检（必须做）

```bash
python $PIPE_DIR/scripts/validate.py style_profile $WORK/style_profile.json
python $PIPE_DIR/scripts/check_style.py --profile $WORK/style_profile.json --inputs $WORK/style_inputs.json
```

失败就按错误信息修改后重跑，最多 3 轮。都通过后，再把 `$WORK/style_profile.json` 复制到 `$CB/state/style_profile.json`。
3 轮仍不通过：**不要**覆盖旧文件，这一步算失败但不影响出题（沿用旧风格文件）。
