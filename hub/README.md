# hub/ — 学校 Hub

负责人：D。云端，对公网可访问（§6.4）。看板数据只来自批准上传的 `coverage_share`。

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload        # API 文档：http://localhost:8000/docs
pytest
```

当前所有接口返回 `contracts/examples` 的 mock（TD1），C 可以直接对接。
mock 认证：`Authorization: Bearer mock-token-<id>`，id 以 `H` 开头为组长、`ADM` 开头为管理员，其余为老师。

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
