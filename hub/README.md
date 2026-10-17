# hub/ — 学校 Hub

负责人：D。云端，对公网可访问（§6.4）。看板数据只来自批准上传的 `coverage_share`。

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload        # API 文档：http://localhost:8000/docs
pytest
```

`/api/join` 和 `/api/syllabus*` 已是真实实现，其余接口仍返回 `contracts/examples` 的 mock（TD1），C 可以直接对接。

考纲（TD3，审批 A4）：组长 `POST /api/syllabus` 上传，Hub 校验格式后存为草稿，版本号自动 +1（上传者填的 `version`、`status` 会被忽略）；组长 `POST /api/syllabus/{id}/approve` 批准最新草稿，并写审计 `approve_syllabus`。`GET /api/syllabus/current` 只返回已批准的最新版本，草稿不生效。Hub 启动时预装 `contracts/examples/syllabus.json` 作为 v1 已批准版本。

加入（TD2）：Hub 启动时自动建好演示工作区 `W1` 和三个邀请码，每种角色一个，码和角色不符会被拒绝：

| 邀请码 | 角色 |
| --- | --- |
| `DEMO-TEACHER` | teacher |
| `DEMO-HEAD` | head |
| `DEMO-ADMIN` | admin |

`POST /api/join` 返回的 token 放在 `Authorization: Bearer <token>`。
联调期仍接受 mock 认证：`Authorization: Bearer mock-token-<id>`，id 以 `H` 开头为组长、`ADM` 开头为管理员，其余为老师。设置 `HUB_MOCK_AUTH=0` 关闭。

| 文件 | 内容 | 任务 |
| --- | --- | --- |
| `app/routes/join.py` | 邀请码加入、token | TD2 |
| `app/routes/syllabus.py` | 考纲草稿、批准（A4）、版本 | TD3 |
| `app/routes/coverage.py` | 接收 / 撤回 coverage_share（A3、A5），覆盖表 | TD4、TD5 |
| `app/routes/dashboard.py` | 三种角色视图 + 考前预警 | TD6 |
| `app/routes/audit.py` | 审计日志 | TD5、TD6 |
| `app/db.py` | SQLite 表结构 | TD2–TD5 |
| `app/auth.py` | token → 角色 | TD2 |
| `app/static/` | 看板前端 | TD6 |

## 待定

- 组长“本年级”的权限过滤需要班级 → 年级的对应关系，目前契约里没有（§4 表格）。
- 考试日期存在工作区设置里，设置接口未定义。
