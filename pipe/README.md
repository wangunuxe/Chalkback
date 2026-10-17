# pipe/ — chalkback-pipe

负责人：A（数据：`scripts/extract_segments.py`、`scripts/read_reports.py`、`prompts/map_kp.md`）
和 B（智能：`pipe.md`、`scripts/validate.py`、`prompts/alerts.md`、`prompts/learn_style.md`、`prompts/gen_quiz.md`、`templates/game.html`）。

`screenpipe pipe install` 安装的就是这个目录，所以它必须自给自足：

- `schemas/` 是 `contracts/*.schema.json` 的副本（`make sync-schemas` 生成，不要手改）。
- 脚本只用标准库，`validate.py` 例外，需要 `jsonschema`（见 `requirements.txt`）。TB6 打包时确认老师电脑上的安装方式。

本地开发：

```bash
python scripts/extract_segments.py --mock --lesson-id L-T1-20261017-1000 \
  --start 2026-10-17T10:00:00+02:00 --end 2026-10-17T11:00:00+02:00 --out /tmp/out/segments.json
python scripts/validate.py segment /tmp/out/segments.json
```
