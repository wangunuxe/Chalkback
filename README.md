# ChalkBack

面向学校的教学助手：screenpipe 在每位老师电脑上记住课堂，chalkback-pipe 下课后生成测验、学生游戏、漏讲提醒和学情；
老师审批后，只有考纲覆盖数据进入学校 Hub。screenpipe 黑客松赛道 3。

**完整设计见 [`ChalkBack 技术文档.md`](./ChalkBack%20技术文档.md)，它是唯一的事实来源。**

## 目录与负责人（§7）

只有负责人合并该目录的改动。

| 目录 | 负责人 | 内容 |
| --- | --- | --- |
| `contracts/` | 全员 | JSON Schema + 示例。周六 13:00 冻结，改动需全员同意 |
| `pipe/` | A + B | chalkback-pipe，`screenpipe pipe install` 安装的就是它 |
| `pipe/scripts/extract_segments.py`、`read_reports.py`、`prompts/map_kp.md` | A | 取数据、对知识点 |
| `pipe/pipe.md`、`scripts/validate.py`、`prompts/{alerts,learn_style,gen_quiz}.md`、`templates/` | B | 编排、出题、提醒、风格 |
| `console/` | C | 老师控制台 :4000（审批 A1–A3、A5 发起） |
| `hub/` | D | 学校 Hub（审批 A4、A5 执行） |
| `demo/`、`docs/DEMO.md` | A | 演示数据与剧本 |
| `docs/SETUP.md` | B | 新老师安装说明 |
| `docs/ADMIN.md` | D | 管理员与组长说明 |
| `tools/`、`tests/`、`Makefile` | 全员 | 开发辅助、契约自检 |

## 开始

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
make check          # 示例全部通过契约 + 各组件测试
make seed-mock      # 用示例生成 .mock-home/（假的 ~/.chalkback/）
make hub            # :8000，所有接口先返回 mock
make console        # :4000，读 .mock-home
```

上游没完成就用 `contracts/examples/` 的 mock 开工，不要等。

## 规则速记

- 契约（§5、§6）是硬约束，不得擅自修改。改了 `contracts/` 记得 `make sync-schemas`。
- 录音、截图、转写原文、screenpipe id 永远不离开老师电脑；上传只能是 `coverage_share`。
- 时间一律 ISO 8601 带时区偏移（Europe/Paris）。代码、字段名、文件名用英文。
- 提交信息写任务编号：`TC3: approve flow writes edits.jsonl`。
