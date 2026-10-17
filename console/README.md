# console/ — 老师控制台

负责人：C。本机 `http://localhost:4000`（§6.3）。老师页面只允许本机访问，`/play/*` 对校园网开放。

```bash
pip install -r requirements.txt
make seed-mock                                   # 在仓库根目录：用 contracts/examples 生成 .mock-home/
CHALKBACK_HOME=../.mock-home uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
pytest
```

| 文件 | 内容 | 任务 |
| --- | --- | --- |
| `app/paths.py` | `~/.chalkback/` 布局；`CHALKBACK_HOME` 可覆盖 | — |
| `app/outbox.py` | 只读有 `ready` 的 outbox 目录 | TC1 |
| `app/share.py` | coverage → coverage_share 白名单转换（隐私边界） | TC3 |
| `app/hub_client.py` | Hub API 调用 | TC2/3/6 |
| `app/routes/setup.py` | 安装向导 + 知情同意（A1） | TC2 |
| `app/routes/review.py` | 审核题目（A2）、批准共享（A3） | TC3 |
| `app/routes/play.py` | 学生游戏、作答、统计 | TC4/5 |
| `app/routes/shares.py` | 共享记录与撤回（A5） | TC6 |
| `app/routes/style.py` | 风格文件只读页 | TC6 |

## 待定

- 作答提交接口（game.html → 控制台）：与 B 在 H9 前约定。
- `state/shares.json` 格式：C 自定，写在这里。
