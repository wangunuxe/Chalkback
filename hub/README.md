# hub/ — 学校 Hub

负责人：D。云端，对公网可访问（§6.4）。看板数据只来自批准上传的 `coverage_share`。

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload        # API 文档：http://localhost:8000/docs
pytest
```

全部接口都是真实实现，数据存在 SQLite（`HUB_DB`）。

看板（TD6）：打开 Hub 首页登录（邀请码，或粘贴控制台 `config.json` 里的 token），进入 `/dashboard.html`。三种角色都登录过以后，顶部可以一键切换；页面每 10 秒刷新，老师撤回后看板会自动更新。页面不依赖外网资源。
- 老师：只看自己的班，每个知识点是否讲过和分钟数，以及“别的班讲了、你还没讲”的知识点（不指明是哪个班）。
- 组长：知识点 × 班级矩阵，考纲面板（上传草稿、批准），待批准草稿列表。
- 管理员：各班进度汇总（不含知识点明细）、邀请码、各角色人数。
- 三种角色都能看审计日志，范围按角色过滤。
- 预警：`剩余未覆盖知识点数 > 距考试剩余周数 × 平均每周覆盖数`。平均每周覆盖数 = 已覆盖数 ÷ 从该班第一节上传课到今天的周数（最少按 1 周算）。考试日期默认 `2026-12-18`，用环境变量 `HUB_EXAM_DATE=YYYY-MM-DD` 覆盖。

彩排数据：Hub 运行时执行 `python hub/scripts/seed_demo.py [https://localhost:8000]`，会通过真实接口上传 3 个班的示例覆盖数据（4A 进度正常，4B 触发预警，T1 能看到同年级对比）。

覆盖表（TD4、TD5，审批 A3、A5）：
- `POST /api/coverage`（老师）：严格按 `coverage_share` schema 校验，多一个字段都返回 422（隐私边界）。同一位老师重传同一节课，新的替换旧的。写审计 `share_coverage`。
- `DELETE /api/coverage/{share_id}`：只有上传者本人能撤回（他人 403，不存在 404），写审计 `revoke`。
- `GET /api/coverage?class_id=`：按当前已批准考纲列出每个知识点，汇总该班全部上传（`covered` 取“任一节讲过”，`minutes` 求和）。老师只能查自己上传过的班。
- `GET /api/audit`：老师看自己的记录，组长、管理员看全校记录。

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

- 组长“本年级”的权限过滤需要班级 → 年级的对应关系，目前契约里没有（§4 表格）。**暂时让组长看全校**（覆盖表和审计日志），演示只有一个年级，效果相同。
- 考试日期存在工作区设置里，设置接口未定义。
