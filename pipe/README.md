# pipe/ — chalkback-pipe

负责人：A（数据：`scripts/extract_segments.py`、`scripts/read_reports.py`、`prompts/map_kp.md`）
和 B（智能：`pipe.md`、`prompts/{alerts,learn_style,gen_quiz}.md`、`templates/game.html`，以及其余脚本）。

`npx -y screenpipe@latest pipe install <GitHub 地址或本地文件夹>` 安装的就是这个目录，所以它必须自给自足：

- `schemas/` 是 `contracts/*.schema.json` 的副本（`make sync-schemas` 生成，不要手改）。
- 老师电脑上**只需要 Python 3.11+**，不用 `pip install`：脚本只用标准库；`validate.py` 没有 jsonschema 时
  自动用内置校验器（`tests/test_validate_engines.py` 保证两者结论一致）。
- `scripts/doctor.py` 做环境自检，SETUP 第 6 步和 pipe.md 第 0 步都会运行。

| 脚本 | 用于 pipe 第几步 | 负责人 |
| --- | --- | --- |
| `doctor.py` | 0（环境自检） | B |
| `current_lesson.py` | 1 | B |
| `extract_segments.py` | 2 | A |
| `read_reports.py` | 4 | A |
| `lookback.py`、`check_alerts.py` | 5 | B |
| `style_inputs.py`、`check_style.py` | 6 | B |
| `plan_quiz.py`、`check_quiz.py`、`build_game.py` | 7 | B |
| `validate.py` | 每一步 | B |

本地开发：

```bash
pip install -r requirements.txt     # 仅开发和测试需要
python -m pytest -q                 # 在 pipe/ 目录下
make seed-mock                      # 在仓库根目录：生成 .mock-home/
CHALKBACK_HOME=../.mock-home python scripts/doctor.py --skip-screenpipe
```
