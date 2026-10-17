# console/ — 老师控制台

负责人：C。本机 `https://localhost:4000`（§6.3，自签证书由 `generate_cert.py` 生成）。所有页面——包括学生游戏 `/play`——都只允许本机访问：
学生在老师电脑的浏览器里作答，不做手机端。

```bash
pip install -r requirements.txt
make teacher        # 在仓库根目录：生成 .mock-home/ 和证书，启动 https://localhost:4000/console
pytest              # 在 console/ 目录下
```

| 文件 | 内容 | 任务 |
| --- | --- | --- |
| `app/paths.py` | `~/.chalkback/` 布局；`CHALKBACK_HOME` 可覆盖 | — |
| `app/contracts.py` | 契约校验、Europe/Paris 时间、JSON 读写；复用 pipe 的 `build_game`、`normalize_answer` | — |
| `app/outbox.py` | 只读有 `ready` 的 outbox 目录 | TC1 |
| `app/quizzes.py` | 逐题审核、发布、整份拒绝；写 `edit_event` | TC3 |
| `app/stats.py` | 判分、`kp_stats`、`weights.json` | TC4/5 |
| `app/share.py` | coverage → coverage_share 白名单转换（隐私边界） | TC3 |
| `app/hub_client.py` | Hub API 调用；Hub 失败时返回 502，不回落到 mock token | TC2/3/6 |
| `app/routes/setup.py` | 安装（A1）：join、写 `config.json`、缓存考纲 | TC2 |
| `app/routes/review.py` | 审核页 `/console`、审核接口（A2）、批准共享（A3） | TC3 |
| `app/routes/play.py` | 学生游戏、作答 | TC4/5 |
| `app/routes/shares.py` | 共享记录与撤回（A5） | TC6 |
| `app/routes/style.py` | 风格文件（只读） | TC6 |

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/console?lesson=` | 老师审核页（HTML） |
| GET | `/review`、`/review/{lesson_id}` | 课程列表；课程详情（quiz、alerts、coverage、kp_stats、share） |
| POST | `/review/{lesson_id}/action` | `{action: approve\|edit\|delete\|reject, q_id, changes?}`；改写 `quiz.json`，返回写入的 `edit_event`。`changes` 只能改 `type`、`prompt`、`choices`、`answer`、`time_limit_s`；`delete`、`reject` 都会去掉这道题 |
| POST | `/review/{lesson_id}/publish` | A2 通过：用 pipe 的 `build_game` 重新生成 `game.html`，`status` → `published` |
| POST | `/review/{lesson_id}/reject` | A2 不通过：`status` → `rejected`，游戏不提供 |
| POST | `/review/{lesson_id}/share` | A3：上传 `coverage_share`；Hub 失败返回 502，本机不记录 |
| GET / DELETE | `/shares`、`/shares/{share_id}` | 共享记录；撤回（A5），Hub 删除成功才删本机记录 |
| POST | `/setup` | `{invite_code, teacher_name, hub_url, timetable, consent: true}` |
| GET | `/play/{quiz_id}` | 已发布的游戏；未发布或不存在都是 404 |
| POST | `/play/{quiz_id}/attempt` | H9：`{nickname, q_id, response, time_ms}` → `{correct, answer}`；超时 `response: null` 算错。每次作答后重算 `state/kp_stats/{quiz_id}.json` 和 `state/weights.json` |

`state/shares.json`：`[{share_id, lesson_id, class_id, shared_at}]`，每节课最多一条（重传替换，与 Hub 一致）。

## 待定 / 未完成

- 超时作答的 `response: null` 不符合 `attempt` 契约，等全员决定。
- Hub 记录 `consent`、`publish_quiz` 需要 D 提供接口。
- `/setup` 的 HTML 向导、按课表写 pipe 定时（等 B 实测 pipe 安装后的名字）、出处截图（等 A 实测截图接口）、教案录入、`/shares` 合并 Hub 审计、`/style` 页面。
