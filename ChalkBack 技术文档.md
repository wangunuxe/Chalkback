# ChalkBack 技术文档

Oct 17, 2026 · @Aurora

ChalkBack 是一个面向学校的教学助手。screenpipe 在每位老师电脑上记住课堂，ChalkBack 的 pipe 下课后自动生成测验和学生游戏、漏讲提醒和学情；老师审批后，只有考纲覆盖数据进入学校 Hub，用于知识点覆盖表和考纲进度看板。本项目参加 screenpipe 黑客松**赛道 3：让它适用于团队**，提交截止 10 月 18 日 19:00。

## 0. 给 AI 协作者的规则

如果你是帮助某位队员写代码的 AI，请先读完本节，再读第 5–9 节中与你的角色相关的部分。

- **先确认角色**：你只服务 A、B、C、D 中的一个角色（见第 8 节）。只在该角色拥有的目录里写代码（见第 7 节）。
- **数据契约是硬约束**：第 5 节的 JSON 格式和第 6 节的接口不得擅自修改。需要改时，先提出，由四位队员一致同意后，同时更新 `contracts/` 和本文档。
- **用 mock 先开工**：上游未完成时，使用 `contracts/examples/` 里的示例数据，不要等待。
- **隐私是硬约束**：录音、截图、转写原文和 screenpipe 的 id 永远不离开老师电脑。上传到 Hub 的数据只能是第 5 节标注为“可共享”的字段。
- **约定**：时间一律用 ISO 8601 带时区（`Europe/Paris`，如 `2026-10-17T10:12:05+02:00`）；代码、字段名、文件名用英文；界面文字用法语或英语（待团队确定）；课堂内容语言以实际演示课程为准。
- **不确定就问**：本文档没有写清楚的地方，先问对应队员，不要自行发明新的数据格式或接口。
- **完成的定义**：满足第 8 节中该任务的验收标准，并能用 `contracts/examples/` 的数据跑通。

## 1. 赛道 3 要求与 ChalkBack 的对应

赛道 3 原文：把个人工作流变成别人也能用的自动化，配备配置、审批和共享工具；需要展示一个别人能用的工作流，包括配置说明和审批步骤。

| 评委要看的 | ChalkBack 的实现 | 证据（demo 或问答时展示） |
| --- | --- | --- |
| 别人能用 | 一位新老师用邀请码加入学校工作区，一条命令安装 pipe，安装向导完成其余配置 | 一位队外人员照 `SETUP.md` 安装的计时结果 |
| 配置说明 | `docs/SETUP.md`：装 screenpipe → 装 pipe → 打开控制台向导 → 完成 | 文档本身 + 新人测试 |
| 审批步骤 | 5 个审批点：安装时知情同意、发布前审核题目、共享前批准覆盖数据、组长批准考纲版本、老师可随时撤回 | 审核页、审计日志、撤回操作 |
| 共享工具 | 共享考纲、共享 pipe、知识点覆盖表、考纲进度看板 | Hub 页面 |
| 角色与权限 | 老师、教研组长、学校管理员三种视图；pipe 只读权限 | 看板切换角色 |
| 信任与隐私 | 原始数据不出老师电脑，只上传批准后的覆盖数据 | 架构图中的边界 |

个人层面的学习能力（agent 从老师过去的出题画面和审核修改中学习风格）保留，作为赛道 2 的基础；它也说明“共享同一个 pipe，每位老师得到的是自己的风格”。

## 2. 系统架构

系统分两个区域，中间只有一道门：老师控制台。所有从老师电脑到学校 Hub 的数据，都必须经过老师在控制台里批准。

&#91;embedded content: ChalkBack 架构 · 高亮的是两个审批与信任组件\]

| 组件 | 运行位置 | 职责 | 负责人 | 建议技术 |
| --- | --- | --- | --- | --- |
| screenpipe | 老师电脑 | 记录老师麦克风转写和屏幕文字；不修改，原样使用 | A 部署 | screenpipe 桌面版（Windows 或 macOS） |
| chalkback-pipe | 老师电脑，由 screenpipe 启动 | 下课后还原课堂、对知识点、出题并生成学生游戏、漏讲提醒、学风格，结果写入 outbox | A 数据部分，B 智能部分 | `pipe.md` + Python 脚本，只调用 screenpipe 本地 API |
| outbox | 老师电脑 `~/.chalkback/outbox/` | pipe 与控制台之间的文件接口 | B 写，C 读 | JSON 文件 |
| 老师控制台 | 老师电脑 `https://localhost:4000` | 安装向导、审核题目、在本机提供学生游戏页面并记录作答、批准共享、共享记录与撤回、与 Hub 同步 | C | FastAPI + 简单前端 |
| 学校 Hub | 云端（对公网可访问，HTTPS） | 工作区与邀请码、共享考纲、知识点覆盖表（接收批准的覆盖数据）、角色看板、审计日志 | D | FastAPI + SQLite + 简单前端 |

技术栈为建议，可以调整，但全队要在第 3 小时前定下并保持一致。

### Agent：ChalkBack 的“大脑”

ChalkBack 里只有一个 agent：运行在老师电脑上的 AI agent。screenpipe 按课表启动 chalkback-pipe 时，会运行一个编程类 agent（默认 pi，也可以是 claude-code），模型在 screenpipe 的 AI 预设里选。控制台和 Hub 都是普通软件，不含 agent。

- **任务说明**：`pipe/pipe.md`（第 6.1 节的 8 步）和 `pipe/prompts/` 下的四个提示词。
- **记忆**：screenpipe 本地数据（只读）、风格文件、过去的覆盖表。
- **工具**：screenpipe `/search`、`pipe/scripts/` 下的脚本、写 outbox、发通知。
- **边界**：只读 screenpipe；不直接上传任何东西；所有产出先进 outbox，等老师审批。

agent 负责需要判断的部分，固定逻辑（取数据、拼片段、校验格式）交给脚本：

| agent 的判断 | 依据 | 产出 |
| --- | --- | --- |
| 每段讲解属于哪个知识点 | 讲解片段 + 考纲 | `coverage` |
| 今天没讲的点要不要回查、是不是以前讲过 | 教案 + 过去 21 天记录 | `alerts` |
| 这位老师出题有什么习惯 | 过去的出题画面 + 审核修改 | `style_profile` |
| 出哪些题、每个知识点几题、怎么写 | 覆盖时长 + 权重 + 风格 | `quiz`（每题带出处）+ 学生游戏页面 game.html |

对赛道 3 的意义：同一个 agent（同一份 pipe）分发给全校，每位老师的 agent 学到的是自己的风格；agent 的权力被只读权限和老师审批框住，学校才敢部署。

## 3. 端到端工作流

分为一次性的加入流程和每节课的循环。标注 **\[审批 Ax\]** 的步骤必须有人点头，对应第 4 节。

**一次性：学校和新老师加入**

1. 学校管理员在 Hub 创建工作区，生成邀请码。
2. 教研组长上传考纲知识点清单并发布为正式版本 **\[审批 A4\]**。
3. 新老师按 `docs/SETUP.md`：安装 screenpipe → 一条命令安装 chalkback-pipe → 启动本机控制台。
4. 控制台安装向导：输入邀请码 → 选择学科和班级 → 填写课表 → 查看并同意“记录什么、什么会上传” **\[审批 A1\]**。向导根据课表把定时规则写入 pipe。

**每节课的循环**

1. **上课**：老师照常上课，screenpipe 记录麦克风转写和屏幕文字。
2. **下课自动运行**：screenpipe 按课表启动 chalkback-pipe（只读权限）。
3. **还原课堂**：取本节课时间窗的转写和课件文字，按时间戳对齐成讲解片段。
4. **对知识点**：生成本节课覆盖表，只存 screenpipe 的时间戳和 id。
5. **生成结果**：漏讲提醒（回查过去 21 天确认）、带出处的测验和学生游戏（按老师风格和学情权重）、Kahoot 报告里的薄弱点。全部写入 outbox，并通知老师。
6. **老师审核题目** **\[审批 A2\]**：通过、修改或拒绝。修改记录回传 pipe，用于更新风格文件。
7. **发布游戏**：控制台在本机（`localhost`）提供 agent 生成的学生游戏页面，老师在自己电脑的浏览器里打开。
8. **学生作答**：学生在老师电脑上打开游戏页面，输入昵称、作答，控制台在本机记录答案和用时。不做手机端，不对校园网开放。
9. **学情回传**：控制台按知识点统计作答，生成权重文件，下次出题使用。
10. **老师批准共享覆盖数据** **\[审批 A3\]**：只上传知识点、是否讲过、时长。
11. **看板更新**：Hub 更新考纲进度和预警，写入审计日志。
12. **随时撤回** **\[审批 A5\]**：老师在控制台撤回任一上传，Hub 删除并记录。

另外，老师可以随时在 Claude 里通过 screenpipe MCP 查询自己的课堂记录（仅在本机，不经过 Hub）。

## 4. 审批、角色与配置

**五个审批点**（每次审批都写一条 `audit_event`，见第 5 节）

| 编号 | 审批什么 | 谁批 | 在哪里 | 不批的结果 | 实现人 |
| --- | --- | --- | --- | --- | --- |
| A1 | 安装时知情同意：记录范围、上传内容、pipe 权限 | 老师 | 控制台安装向导 | 无法完成安装 | C |
| A2 | 题目发布前审核 | 老师 | 控制台审核页 | 题目不发布 | C |
| A3 | 覆盖数据上传前批准 | 老师 | 控制台审核页 | 数据留在本机 | C |
| A4 | 考纲版本发布 | 教研组长 | Hub 考纲页 | 新版本不生效，继续用旧版 | D |
| A5 | 撤回已上传数据 | 老师 | 控制台共享记录页 | — | C 发起，D 执行删除 |

**角色与权限**

| 内容 | 老师 | 教研组长 | 学校管理员 |
| --- | --- | --- | --- |
| 自己的录音、截图、转写 | 仅本机 | 看不到 | 看不到 |
| 自己的题目和学情 | 可看 | 看不到（只在老师本机） | 看不到 |
| 班级考纲进度 | 自己的班 | 本年级各班 | 全校各班 |
| 与同年级对比的漏讲点 | 只给本人 | 看不到个人对比 | 看不到 |
| 共享考纲 | 只读 | 编辑并发布 | 只读 |
| 工作区与邀请码 | — | — | 管理 |
| 审计日志 | 自己的记录 | 本年级记录 | 全部记录（不含内容本身） |

**共享配置 vs 个人配置**

| 配置 | 范围 | 存在哪里 |
| --- | --- | --- |
| chalkback-pipe 本体（`pipe.md`、脚本、提示词、权限规则） | 全校共享，同一版本 | GitHub 仓库 `pipe/` |
| 考纲知识点清单 | 全校共享，按版本 | Hub |
| 工作区、班级列表 | 全校共享 | Hub |
| 课表、教案、自动共享开关 | 个人 | `~/.chalkback/config.json`、`~/.chalkback/lesson_plans/` |
| 出题风格文件 | 个人，永不上传 | `~/.chalkback/state/style_profile.json` |
| 大模型 API key | 个人或学校统一 | screenpipe 的 AI 预设（不写入代码仓库） |

## 5. 数据契约

全部是 JSON。每种格式在 `contracts/` 里有 JSON Schema，在 `contracts/examples/` 里有一个可用的示例文件，由全员在第 3 小时前定稿。下面的示例内容（法语语法、班级 4A）只是占位，实际主题待定。

| 契约 | 产生方 → 使用方 | 位置 | 能否离开老师电脑 |
| --- | --- | --- | --- |
| `syllabus` | D → A、B、C | Hub；本机缓存 `~/.chalkback/cache/syllabus.json` | 本来就在 Hub |
| `lesson_plan` | C（老师填）→ B | `~/.chalkback/lesson_plans/{class_id}/{date}.json` | 否 |
| `segment` | A → B | outbox `segments.json` | 否 |
| `coverage` | A → B、C | outbox `coverage.json` | 只能以 `coverage_share` 形式 |
| `quiz` | B → C | outbox `quiz.json` + 学生游戏页面 `game.html` | 否（只在本机生成和提供游戏） |
| `alerts` | B → C | outbox `alerts.json` | 否 |
| `style_profile` | B → B | `~/.chalkback/state/style_profile.json` | 否 |
| `edit_event` | C → B | `~/.chalkback/state/edits.jsonl` | 否 |
| `weights` | C → B | `~/.chalkback/state/weights.json` | 否 |
| `attempt` | 学生游戏 → C | 本机 `~/.chalkback/state/attempts.jsonl` | 否 |
| `kp_stats` | C（本机统计）→ C | 本机 | 否 |
| `audit_event` | D | Hub | 本来就在 Hub |

**syllabus**

```json
{"syllabus_id": "fr-grammaire-4e", "version": 1, "status": "approved", "subject": "français", "level": "4e",
 "knowledge_points": [{"kp_id": "KP01", "title": "Le passé composé avec avoir", "keywords": ["passé composé", "avoir"]}]}
```

**lesson\_plan**

```json
{"class_id": "4A", "date": "2026-10-17", "syllabus_id": "fr-grammaire-4e", "kp_ids": ["KP01", "KP02", "KP03"]}
```

**segment**（`lesson_id` 格式：`L-{teacher_id}-{YYYYMMDD}-{HHMM}`）

```json
{"segment_id": "S-L-T1-20261017-1000-003", "lesson_id": "L-T1-20261017-1000",
 "start": "2026-10-17T10:12:05+02:00", "end": "2026-10-17T10:16:40+02:00",
 "speech": "…转写原文…", "slide_text": "…当时屏幕上的课件文字…", "app_name": "PowerPoint",
 "evidence": {"transcription_ids": [812, 813], "frame_ids": [5531]}}
```

**coverage**（本机完整版）

```json
{"lesson_id": "L-T1-20261017-1000", "teacher_id": "T1", "class_id": "4A", "syllabus_id": "fr-grammaire-4e", "syllabus_version": 1,
 "generated_at": "2026-10-17T11:05:00+02:00",
 "points": [{"kp_id": "KP03", "covered": true, "minutes": 4.5, "segment_ids": ["S-L-T1-20261017-1000-003"]}]}
```

**coverage\_share**（唯一允许上传的覆盖格式，由 C 从 `coverage` 生成）

```json
{"lesson_id": "L-T1-20261017-1000", "class_id": "4A", "date": "2026-10-17", "syllabus_id": "fr-grammaire-4e", "syllabus_version": 1,
 "points": [{"kp_id": "KP03", "covered": true, "minutes": 4.5}]}
```

**quiz**（只在本机使用；游戏页面不显示每题的 `source`）

```json
{"quiz_id": "Q-L-T1-20261017-1000", "lesson_id": "L-T1-20261017-1000", "class_id": "4A", "status": "pending", "style_profile_version": 2,
 "questions": [{"q_id": "Q1", "kp_id": "KP03", "type": "mcq", "prompt": "…", "choices": ["…", "…", "…", "…"], "answer": 1, "time_limit_s": 20,
   "source": {"segment_id": "S-L-T1-20261017-1000-003", "quote": "…课上原话…", "frame_ids": [5531]}}]}
```

`type` 取值：`mcq` | `fill_blank` | `true_false`。`mcq` 的 `answer` 是选项下标，`fill_blank` 的是字符串，`true_false` 的是布尔值。`status`：`pending` | `approved` | `rejected` | `published`。

**alerts**

```json
{"lesson_id": "L-T1-20261017-1000",
 "missed": [{"kp_id": "KP02", "note": "教案计划讲，本节和过去 21 天都未讲"}],
 "covered_before": [{"kp_id": "KP01", "last_covered_at": "2026-10-14T10:20:00+02:00"}],
 "weak_from_reports": [{"kp_id": "KP03", "source": "kahoot_report", "seen_at": "2026-10-16T18:02:00+02:00"}]}
```

**style\_profile**

```json
{"teacher_id": "T1", "version": 2, "updated_at": "2026-10-17T11:06:00+02:00",
 "rules": [{"rule": "偏好填空题", "origin": "screen_history", "evidence": {"frame_ids": [4410], "timestamp": "2026-10-15T14:20:00+02:00"}},
           {"rule": "干扰项用学生常见错误", "origin": "teacher_edit", "evidence": {"edit_ids": ["E3"]}}]}
```

**edit\_event**（`edits.jsonl` 每行一条）

```json
{"edit_id": "E3", "quiz_id": "Q-L-T1-20261017-1000", "q_id": "Q1", "action": "edit", "before": {}, "after": {}, "at": "2026-10-17T11:20:00+02:00"}
```

`action`：`edit` | `delete` | `approve` | `reject`。`before` / `after` 是完整的题目对象。

**weights**

```json
{"class_id": "4A", "updated_at": "2026-10-17T12:00:00+02:00", "weights": {"KP03": 2.0, "KP01": 1.0}}
```

权重规则：默认 1.0；正确率低于 50% 设为 2.0；来自 Kahoot 报告的薄弱点加 0.5。

**attempt**

```json
{"quiz_id": "Q-L-T1-20261017-1000", "nickname": "lapin42", "q_id": "Q1", "response": 2, "correct": false, "time_ms": 8400, "at": "2026-10-17T11:30:12+02:00"}
```

**kp\_stats**

```json
{"quiz_id": "Q-L-T1-20261017-1000", "class_id": "4A", "n_players": 18,
 "by_kp": [{"kp_id": "KP03", "accuracy": 0.41, "avg_time_ms": 12000}]}
```

**audit\_event**

```json
{"event_id": "EV-0007", "workspace_id": "W1", "actor": {"role": "teacher", "id": "T1"},
 "action": "share_coverage", "target_id": "L-T1-20261017-1000", "at": "2026-10-17T12:01:00+02:00"}
```

`action`：`join` | `consent` | `publish_quiz` | `share_coverage` | `revoke` | `approve_syllabus`。

## 6. 接口

### 6.1 chalkback-pipe（A + B）

`pipe/pipe.md` 的开头：

```markdown
---
schedule: manual
enabled: true
timeout: 900
permissions:
  allow:
    - Content(audio, ocr, accessibility)
  deny:
    - App(1Password)
    - Window(*incognito*)
    - Window(*privée*)
---
```

- `schedule` 由控制台向导按课表改写为 cron（例：周一至周五 11:05 为 `5 11 * * 1-5`），通过 screenpipe API `POST /pipes/chalkback/config` 写入。demo 时用 `npx -y screenpipe@latest pipe run chalkback` 手动触发。
- 权限：官方 `reader` 预设只允许 `/search` 等少数接口，**不包含 `/raw_sql`**。所以数据提取一律用 `GET /search`。上面的自定义规则是草案，A 在第 3 小时前用官方文档和实际运行确认。
- 本地 API 认证：每个请求带 `Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY`（screenpipe 运行 pipe 时自动注入）。
- 模型：在 screenpipe 的 AI 预设里配置；用 Claude 需要 Anthropic API key，Pro/Max 订阅不行。

pipe 正文按顺序执行：

1. 读取上下文头和 `~/.chalkback/config.json`，确定刚结束的课（`lesson_id`、`class_id`、开始和结束时间）。
2. `python scripts/extract_segments.py --start <ISO> --end <ISO> --out <outbox>/segments.json`（A）。
3. 按 `prompts/map_kp.md` 生成 `coverage.json`，并用 `scripts/validate.py coverage` 校验（A）。
4. `python scripts/read_reports.py --days 7`：搜索窗口标题含 Kahoot 报告的屏幕文字，输出薄弱知识点（A）。
5. 按 `prompts/alerts.md` 对比 `lesson_plan`；对本节未讲的点，用 `/search` 显式指定过去 21 天的时间范围回查（默认回看窗口最多 8 小时）；输出 `alerts.json`（B）。
6. 若 `style_profile.json` 不存在，或 `edits.jsonl` 有新记录：按 `prompts/learn_style.md` 更新风格文件（B）。
7. 按 `prompts/gen_quiz.md` 用覆盖表、权重、风格文件生成 `quiz.json`，每题带 `source`，再用模板生成学生游戏页面 game.html（读取 quiz.json，作答提交到控制台），并校验（B）。
8. 写入 outbox，最后写 `ready` 标记文件；`POST http://localhost:11435/notify` 通知老师（B）。

用到的 screenpipe 接口：`GET /search`，参数 `content_type`（`audio` / `ocr` / `accessibility`）、`start_time`、`end_time`、`app_name`、`window_name`、`q`、`limit`、`offset`。音频结果用 `device_type = input` 只取麦克风。溯源截图由控制台在本机读取，接口以 A 的实测为准。

### 6.2 outbox 文件接口（B 写，C 读）

```
~/.chalkback/
  config.json                 # C 写，B 读
  cache/syllabus.json         # C 从 Hub 拉取
  lesson_plans/{class_id}/{date}.json
  outbox/{lesson_id}/segments.json | coverage.json | alerts.json | quiz.json | game.html | ready
  state/style_profile.json | edits.jsonl | weights.json | shares.json | attempts.jsonl
```

规则：C 只处理有 `ready` 文件的目录；B 不修改已有 `ready` 的目录。`config.json` 示例：

```json
{"hub_url": "https://<hub>", "token": "<from join>", "teacher_id": "T1", "workspace_id": "W1", "syllabus_id": "fr-grammaire-4e",
 "timetable": [{"day": "MON", "start": "10:00", "end": "11:00", "class_id": "4A"}], "auto_share": false, "consent_at": "2026-10-17T09:30:00+02:00"}
```

### 6.3 老师控制台（C）

本机 `https://localhost:4000`（自签证书，由 `console/generate_cert.py` 生成；第一次打开时浏览器会提示证书不受信任，确认继续即可）；所有页面（包括 `/play` 和作答接口）都只允许本机访问。学生游戏只在老师电脑上的浏览器里打开，不做手机端。

| 页面 | 功能 |
| --- | --- |
| `/setup` | 邀请码 → 学科班级 → 课表 → 知情同意（A1）→ 写 `config.json` 和 pipe 定时 |
| `/review` | 列出 outbox；显示漏讲提醒；逐题通过 / 修改 / 删除（A2）；点开出处显示原话和截图；批准共享覆盖数据（A3） |
| `/play/{quiz_id}` | 学生游戏：在本机提供 agent 生成的 `game.html`；接收作答写入 `attempts.jsonl`；按知识点统计得到 `kp_stats` 和 `weights.json` |
| `/shares` | 已上传记录（来自 `shares.json` 和 Hub 审计）；撤回（A5） |
| `/style` | 只读展示风格文件及每条规则的来源 |

### 6.4 学校 Hub API（D）

全部接口走 HTTPS（Docker 部署为 `https://<hub>:8443`，证书由 `hub/generate_cert.py` 生成）。认证：`POST /api/join` 返回的 token，放在 `Authorization: Bearer <token>`；token 对应一个角色。看板数据只来自批准上传的覆盖表。

| 方法 | 路径 | 角色 | 输入 | 输出 |
| --- | --- | --- | --- | --- |
| POST | `/api/join` | 任何人 | `{invite_code, display_name, role}` | `{teacher_id, token, workspace_id}` |
| GET | `/api/syllabus/current` | 全部 | — | `syllabus` |
| POST | `/api/syllabus` | 组长 | `syllabus`（草稿） | `{syllabus_id, version}` |
| POST | `/api/syllabus/{id}/approve` | 组长 | — | `syllabus`（A4） |
| POST | `/api/coverage` | 老师 | `coverage_share` | `{share_id}`（A3） |
| DELETE | `/api/coverage/{share_id}` | 老师本人 | — | `204`（A5） |
| GET | `/api/coverage?class_id=` | 按第 4 节权限 | — | 知识点覆盖表（该班已讲 / 未讲的知识点及时长） |
| GET | `/api/dashboard?view=teacher\|head\|admin` | 对应角色 | — | 考纲进度与预警 |
| GET | `/api/audit` | 全部，按角色过滤 | — | `audit_event[]` |

预警规则（看板）：`剩余未覆盖知识点数 > 距考试剩余周数 × 该班过去平均每周覆盖数` 时显示“考前讲不完”。考试日期存在工作区设置里。

## 7. 代码仓库结构

一个 GitHub 仓库 `chalkback`，每个目录一个负责人，只有负责人合并该目录的改动。

```
chalkback/
  contracts/                 # 全员共有；第 3 小时冻结，改动需全员同意
    *.schema.json
    examples/*.json          # 每种契约一个可用示例，各角色的 mock
  pipe/                      # A + B（通过 screenpipe pipe install 安装的就是这个目录）
    pipe.md                  # B
    scripts/extract_segments.py   # A
    scripts/read_reports.py       # A
    scripts/validate.py           # B
    prompts/map_kp.md             # A
    prompts/alerts.md             # B
    prompts/learn_style.md        # B
    prompts/gen_quiz.md           # B
    templates/game.html           # B：学生游戏页面模板，agent 据此生成每节课的 game.html
  console/                   # C：本机控制台（后端 + 前端），包括学生游戏的提供与作答记录
  hub/                       # D：Hub 后端、知识点覆盖表、看板前端、数据库
  demo/                      # A：演示数据、教案、考纲、录屏脚本
  docs/
    SETUP.md                 # B：新老师安装说明
    ADMIN.md                 # D：学校管理员与组长说明
    DEMO.md                  # A：演示步骤与备用方案
```

## 8. 分工

四个角色，按架构分层。任务编号 `TA1`、`TB1`…… 用于沟通和提交信息（与审批点 A1–A5 无关）。截止时间对应第 10 节的检查点。

### 角色 A：记忆与数据层

负责从 screenpipe 取出课堂并对到知识点。拥有：`pipe/scripts/extract_segments.py`、`pipe/scripts/read_reports.py`、`pipe/prompts/map_kp.md`、`demo/`、`docs/DEMO.md`。

| 任务 | 交付物 | 验收标准 | 截止 |
| --- | --- | --- | --- |
| TA1 在两台演示电脑（老师 T1、T2）装好 screenpipe，实测 `/search` 的字段和权限规则 | 实测记录（字段名、返回示例、权限是否放行）提交到 `demo/` | 全队能据此写代码 | 周六 13:00 |
| TA2 `extract_segments.py`：按时间窗取麦克风转写和课件文字，按时间戳对齐成片段（按换页切分，每段约 2–5 分钟） | 脚本 | 输出通过 `segment` 校验；在只读权限下运行 | 周六 20:00 |
| TA3 `map_kp.md` 提示词，生成 `coverage.json` | 提示词 + 一份真实输出 | 输出通过 `coverage` 校验 | 周六 20:00 |
| TA4 映射效果评估：人工标注一节演示课的知识点，和输出对比 | 一个准确率数字 + 说明 | 可写进答辩 | 周日 09:00 |
| TA5 `read_reports.py`：从屏幕文字读出 Kahoot 报告页的薄弱题目并对到知识点 | 脚本 | 对演示报告页输出正确的 `weak_from_reports` | 周日 01:00 |
| TA6 演示数据：与 D 定考纲；写教案；T1、T2 各录 2 节课（含一节“上周”的课）；T1、T2 各在出题平台手动出 3–4 套风格明显不同的题；T1 打开一次 Kahoot 报告页 | screenpipe 里的真实记录 + `demo/` 里的考纲和教案 | B 和 C 能用真实数据联调 | 周六 20:00 |
| TA7 `DEMO.md`、备用录屏、组织彩排 | 文档 + 视频 | 彩排两次且在 3 分钟内 | 周日 17:00 |

### 角色 B：Agent 与学习层

负责 pipe 的编排、出题、提醒、学风格和安装。拥有：`pipe/pipe.md`、`pipe/scripts/validate.py`、`pipe/prompts/alerts.md`、`pipe/prompts/learn_style.md`、`pipe/prompts/gen_quiz.md`、`docs/SETUP.md`。

| 任务 | 交付物 | 验收标准 | 截止 |
| --- | --- | --- | --- |
| TB1 `validate.py`：按 `contracts/` 校验任一契约文件 | 脚本 | 对 `examples/` 全部通过，对错误文件报错 | 周六 13:00 |
| TB2 `pipe.md` 编排第 6.1 节的 8 步 | pipe | 用 mock 片段 `pipe run chalkback` 产出完整 outbox | 周六 20:00 |
| TB3 `gen_quiz.md`：按覆盖时长和权重分配题量，只考讲过的知识点，每题带 `source`；再用 `templates/game.html` 生成学生游戏页面 `game.html` | 提示词 + 游戏模板 + 真实输出 | 通过 `quiz` 校验；每题 `source.quote` 能在转写中找到；`game.html` 在老师电脑的浏览器里能打开并作答 | 周六 20:00 |
| TB4 `alerts.md` + 过去 21 天回查 | 提示词 | 演示数据上正确区分“未讲”和“上周讲过” | 周日 01:00 |
| TB5 `learn_style.md`：从老师过去 30 天的出题画面（窗口含 Kahoot、Quizlet、Forms）和 `edits.jsonl` 生成风格文件，每条规则带证据 | 提示词 + T1、T2 两份风格文件 | 两份文件明显不同；同一节课生成的题目风格不同 | 周日 09:00 |
| TB6 打包：pipe 能从 GitHub 一条命令安装；写 `SETUP.md` | 文档 + 可安装的 pipe | 在一台干净的电脑上按文档装好 | 周日 09:00 |
| TB7 新人测试：请一位队外人员照 `SETUP.md` 安装并计时，按问题修文档 | 计时结果 + 修订后的文档 | 答辩里可引用的真实数字 | 周日 13:00 |

### 角色 C：老师端与审批层

负责老师和学生看到的界面，以及所有老师端审批。拥有：`console/`。

| 任务 | 交付物 | 验收标准 | 截止 |
| --- | --- | --- | --- |
| TC1 控制台骨架，读取 outbox（先用 mock） | 可运行的控制台 | 列出 mock 课程和题目 | 周六 13:00 |
| TC2 `/setup` 向导：邀请码加入、课表、知情同意页（A1）、写 `config.json`、通过 screenpipe API 写 pipe 定时 | 页面 | 新用户不碰代码完成配置；审计中有 `join` 和 `consent` | 周日 01:00 |
| TC3 `/review`：逐题审核（A2）、点开出处显示原话和截图、漏讲提醒、批准共享（A3）；写 `edits.jsonl`；生成 `coverage_share` 并上传 | 页面 | 上传内容不含任何原文和 screenpipe id | 周六 20:00（mock）/ 周日 01:00（接 Hub） |
| TC4 学生游戏 `/play`：在本机（`localhost`）提供 agent 生成的 `game.html`；输入昵称、逐题计时、作答写入 `attempts.jsonl` | 功能 | 三种题型都能作答；同一台电脑上多位学生先后作答（不同昵称）都能正确记录 | 周日 01:00 |
| TC5 本机按知识点统计 `attempts.jsonl` 得到 `kp_stats`，按第 5 节规则生成 `weights.json` | 功能 | 下一次出题使用新权重 | 周日 09:00 |
| TC6 `/shares` 共享记录与撤回（A5）；`/style` 只读风格页 | 页面 | 撤回后 Hub 看板不再显示，审计有 `revoke` | 周日 09:00 |

### 角色 D：学校 Hub 与共享层

负责所有多人共享的部分、部署和答辩幻灯片。拥有：`hub/`、`docs/ADMIN.md`。

| 任务 | 交付物 | 验收标准 | 截止 |
| --- | --- | --- | --- |
| TD1 部署方式和公网地址；API 骨架按第 6.4 节返回 mock | 公网 URL + mock API | 公网浏览器能打开；C 能对接 | 周六 13:00 |
| TD2 工作区、邀请码、`/api/join`、角色 token | 接口 | 三种角色各能加入 | 周六 20:00 |
| TD3 考纲草稿、组长批准、版本（A4） | 接口 + 页面 | 未批准的版本不生效 | 周日 01:00 |
| TD4 知识点覆盖表：接收批准的 `coverage_share`，按班级、年级汇总，提供 `/api/coverage` | 接口 | 与 TC3 上传联调通过 | 周日 01:00 |
| TD5 覆盖数据接收与撤回（A3、A5）、审计日志 | 接口 | 每次审批和撤回都有 `audit_event` | 周日 01:00 |
| TD6 看板三种视图 + 考前预警 + 审计列表 | 页面 | 切换角色后可见内容符合第 4 节的权限表 | 周日 09:00 |
| TD7 `ADMIN.md`；答辩幻灯片（含商业模式和隐私边界一页） | 文档 + 幻灯片 | 彩排使用 | 周日 13:00 |

## 9. 角色之间的交接

每一行是一次交接：到期前使用方用 mock 开发，到期后切换到真实产出。每次交接完成，提供方在群里发一句“交接编号 + 位置”。

| 编号 | 提供方 → 使用方 | 交付什么 | 到期 | 到期前用 |
| --- | --- | --- | --- | --- |
| H1 | 全员 → 全员 | `contracts/` schema + examples，冻结 | 周六 13:00 | 本文档第 5 节 |
| H2 | A → 全员 | screenpipe `/search` 实测记录（TA1） | 周六 13:00 | 官方文档 |
| H3 | D → C | Hub 公网地址 + mock API（TD1） | 周六 13:00 | 本地假服务 |
| H4 | D + A → 全员 | 演示考纲 `syllabus` | 周六 13:00 | `examples/syllabus.json` |
| H5 | A → B | 真实 `segments.json` 与 `coverage.json`（TA2、TA3） | 周六 20:00 | `examples/` |
| H6 | A → B、C | screenpipe 里的真实演示记录（TA6） | 周六 20:00 | — |
| H7 | B → C | 完整 outbox（TB2、TB3） | 周六 20:00 | `examples/` |
| H8 | C → D | 上传的 `coverage_share`（TC3） | 周日 01:00 | 用 curl 发 examples |
| H9 | B → C | agent 生成的学生游戏页面 `game.html`（TB3） | 周六 20:00 | 手写示例页面 |
| H10 | C → B | `edits.jsonl`（TC3）、`weights.json`（TC5） | 周日 01:00 / 09:00 | 手写示例文件 |
| H11 | B → 全员 | 可安装的 pipe + `SETUP.md`（TB6） | 周日 09:00 | 本地文件夹安装 |
| H12 | 全员 → A | 各自演示片段可用，用于彩排和备用录屏 | 周日 13:00 | — |

**协作规则**

- 关键路径是 H5 → H7 → H8：A 或 B 延误会拖住端到端。任何一方预计超时 1 小时以上，立刻在群里说，其他人继续用 mock。
- 改契约：在群里提出字段和理由 → 受影响的角色同意 → 同时改 `contracts/`、示例和本文档。
- 每个检查点开 5 分钟站会：每人说完成了什么、卡在哪、下一个检查点要交什么。
- 提交信息写任务编号，例如 `TC3: approve flow writes edits.jsonl`。

## 10. 时间线与检查点

从现在到提交约 34 小时。每个检查点的“完成”必须可以演示，不是“代码写了一半”。

1. **周六 13:00 · 开工就绪**：契约冻结（H1）；screenpipe 实测（H2）；Hub 公网地址和 mock（H3）；演示考纲（H4）；全队定下技术栈和大模型 API key。
2. **周六 20:00 · 各自跑通**：每个组件用 mock 独立运行；演示课、出题画面、Kahoot 报告页录完（H6）。
3. **周日 01:00 · 第一次端到端**：真实录课 → pipe → outbox → 审核 → 本机游戏作答 → 统计 → 批准共享到 Hub。完成后按需轮流睡觉。
4. **周日 09:00 · 赛道 3 功能齐全**：五个审批点、撤回、审计日志、三种角色视图、风格学习、`SETUP.md`。
5. **周日 13:00 · 功能冻结**：队外新人安装测试（TB7）；录备用演示视频；幻灯片定稿。之后只修 bug。
6. **周日 17:00 · 彩排**：完整走两遍，每遍计时不超过 3 分钟；准备问答素材。
7. **周日 19:00 · 提交**。

睡觉建议错开：A、B 在第一次端到端后先睡；C、D 在周日凌晨继续做审批和看板，周日早上补睡。每人至少 5 小时。

## 11. Demo 剧本（3 分钟）

主线是“一个老师的工作流，变成全校都能用的自动化”。现场不讲课，使用提前录好的数据。

| 时间 | 画面 | 要说的重点 | 负责 |
| --- | --- | --- | --- |
| 0:00–0:15 | 开场页 | 痛点；“老师照常上课，screenpipe 记住课堂” | D |
| 0:15–0:35 | 新老师加入：`SETUP.md` 一条命令 + 安装向导和知情同意页 | “一位队外新人 X 分钟装好”（用 TB7 的真实数字） | B |
| 0:35–1:10 | 下课后 pipe 自动产出：漏讲提醒 + 测验；点开一道题显示原话和课件截图；并排展示 T1、T2 同一份 pipe 学出的不同风格 | 共享一个 pipe，每位老师得到自己的风格 | A |
| 1:10–1:35 | 老师审核通过 → 在本机打开游戏页面答一题 → 作答统计（含提前准备的全班作答数据）：“第 2 题大家都错，下次加权” | 没有审核就不会发布 | C |
| 1:35–2:05 | 批准共享 → 看板切换三种角色：老师、组长、管理员；考前预警 | 不同角色看到不同内容；及时调整方向 | D |
| 2:05–2:30 | 审计日志 → 老师点“撤回”→ 看板更新 | 每一次共享都经老师批准、可追溯、可撤回；录音从未离开电脑 | C |
| 2:30–3:00 | 架构图 + 商业模式一页 | 学校按年订阅；可通过 screenpipe Teams 部署到全校 | D |

问答素材（录屏备好）：老师改题后风格文件 v1→v2 并重新生成；回查过去 21 天避免误报：读取 Kahoot 报告；组长批准考纲新版本；映射准确率（TA4）；在 Claude 里通过 MCP 提问。

## 12. 风险与待确认

| 风险或问题 | 应对 | 负责 | 截止 |
| --- | --- | --- | --- |
| 比赛是否要选定赛道、是否按赛道评奖 | 问现场组织者 | D | 周六 13:00 |
| 只读权限下部分接口不可用 | 只用 `/search`；按 TA1 实测调整权限规则 | A | 周六 13:00 |
| 屏幕文字质量：Linux 上主要靠 OCR | 演示电脑用 Windows 或 macOS | A | 周六 13:00 |
| 大模型 API key 与费用 | 定下模型和提供方；在 screenpipe AI 预设里配置；key 不进仓库 | B | 周六 13:00 |
| 演示课的学科、年级、语言和考纲未定 | 全队定一个具体主题，知识点控制在 8–12 个 | A + D | 周六 13:00 |
| 知识点映射不准 | 先用一节课验证（TA3、TA4）；必要时加关键词规则兜底 | A | 周六 20:00 |
| pipe 超时或回看窗口不够 | `timeout: 900`；提示词里显式指定起止时间 | B | 周六 20:00 |
| 游戏只在老师电脑上作答，现场作答人数少，统计和权重不明显 | 提前用多个昵称准备一份全班 `attempts.jsonl` 作为演示数据；现场只演示答一题 | C | 周六 20:00 |
| Kahoot 报告页读不准 | 只作为加分项；学情以自制游戏数据为主 | A | 周日 01:00 |
| 现场网络或程序出问题 | 备用录屏；所有演示数据提前生成 | A | 周日 13:00 |
| 评委质疑“监控老师” | 答辩主动讲第 4 节的权限表和隐私边界；只录老师麦克风，学生只用昵称 | D | 周日 13:00 |
| 界面语言（法语或英语）未定 | 按评委构成决定 | 全员 | 周六 13:00 |

## 13. 未完成清单

2026-10-17 对照第 3–12 节逐条检查仓库的结果（基于 `main` @ `d9e5db6`，加上本地已修好的 C 部分）。`make check` 通过（204 个测试，其中控制台 47 个），下面是测试覆盖不到、或文档要求了但还没做的部分。做完一项就勾掉；有新发现就加进来。

### 13.1 需要全队决定（涉及契约或接口，按第 0 节需一致同意）

- [ ] **A1、A2 的审计**：`audit_event` 有 `consent`、`publish_quiz`，但第 6.4 节没有接口能把它们写进 Hub，第 4 节“每次审批都写一条 audit_event”和 TC2 验收都做不到。二选一：新增 `POST /api/audit`（只收这两种），或把第 4 节改成 A1、A2 只在本机记录。（C + D）
- [ ] **组长“本年级”权限**：契约里没有班级 → 年级的对应关系，Hub 目前让组长看全校。定下来后改第 4 节或加字段。（D）
- [ ] **考试日期**：第 6.4 节说存在工作区设置里，但没有设置接口，现在只能用环境变量 `HUB_EXAM_DATE`（默认 `2026-12-18`）。（D）
- [ ] **超时作答**：游戏超时提交 `response: null`，控制台按答错记录，但 `attempt` schema 不允许 null（`pipe/templates/game.html:11`）。（B + C）
- [ ] **填空题判分规则**（忽略大小写和多余空格）写进 `contracts/`（`pipe/scripts/check_quiz.py:15`）。控制台已经直接用这套规则判分。（B + C）
- [ ] **演示主题和考纲**：仍是 4 个知识点的法语占位，第 12 节要求 8–12 个；`demo/syllabus/` 为空（H4）。（A + D）
- [ ] 大模型提供方、模型和费用上限没有记录。（B）
- [ ] 界面语言（法语或英语）。（全员）
- [ ] 是否需要选定赛道：问组织者并记下结果。（D）

### 13.2 阻塞演示，优先修

- [x] **控制台 HTTPS 在宿主机跑不起来**：`console/generate_cert.py` 改为写到自己所在的 `console/` 目录，已有证书就不重新生成；`make teacher` 已在 macOS 上实测 `https://127.0.0.1:4000` 可用。（C）
- [x] **Hub HTTPS 在宿主机跑不起来**：`hub/generate_cert.py` 写到自己所在的目录，`make hub` 改为 HTTPS。（D）
- [x] **`edits.jsonl` 不符合 `edit_event`**：控制台现在写完整的 `edit_event`（`edit_id`、`quiz_id`、`before`、`after`），pipe 第 6 步 `style_inputs.py` 能读；`setup.py`、`shares.py` 不再写非契约记录。（C）
- [x] **TC5 没有实现**：每次作答后重算 `state/kp_stats/{quiz_id}.json` 和 `state/weights.json`（默认 1.0；正确率 < 50% → 2.0；Kahoot 薄弱点 +0.5）。（C）
- [x] **超时作答被判为正确**：现在一律算错；`mcq` 也不再把 `true` 当作下标 1。（C）
- [x] **审核只记日志**：通过、修改、删除、拒绝都会改写 `quiz.json`；发布时重新生成 `game.html`；只有已发布的测验才能在 `/play` 打开（A2）；审核页有审核、发布、共享、撤回按钮。（C）
- [x] **共享失败时显示成功**：Hub 不通或拒绝时返回 502，本机不记录；撤回时 Hub 删除成功才删本机记录。（C）
- [x] **`read_reports.py` 编造薄弱点**：现在找不到报告输出 `[]`，出错写 `[]` 并退出 1。（A）
- [x] **公网 Hub 的安全**：mock token 和 `DEMO-*` 邀请码默认关闭，只在联调模式下可用；首页不再公开邀请码。（D）控制台也不再回落到 `mock-token-T1`（C）。正式模式没有 mock T1，真实加入的 T1 不会和它混淆。
- [x] **mock 片段的 lesson_id**：`extract_segments.py --mock` 现在用 `--lesson-id` 和 `--start`，outbox 目录名和文件里的 `lesson_id` 一致。（A）
- [x] **mock 课表不一致**：`current_lesson.py --mock` 固定处理示例课之后的周一那节课，seed 给它写了教案。（B）

### 13.3 角色 A

已修（pipe 测试从 117 个增加到 150 个）：

- [x] TA2 `extract_segments.py`：短于 2 分钟的页并进相邻片段，长于 5 分钟的平均切开；邮件、聊天、密码管理器等窗口的文字一律丢弃，别的 app 的短暂画面不进 `slide_text`；不再编造 `app_name`（不知道就是空字符串）；时间统一为 Europe/Paris；没有讲话的片段不输出，整节课没讲话时输出 `[]`；同时读 accessibility 文字（旧版 screenpipe 不支持时只用 ocr）；每段保留最多 5 个截图 id；`device_type` 大小写不敏感；`--mock` 用本节课的 `lesson_id` 和时间；补了单元测试。
- [x] TA3 `prompts/map_kp.md` 写明判断规则（以老师原话为准、顺口提到不算、每段最多 2 个知识点、关键词兜底）、分钟数和 `covered` 的算法、`lesson_id` / `teacher_id` / `class_id` 只从 `$WORK/lesson.json` 取；新增 `scripts/check_coverage.py` 检查这些规则。`demo/coverage.json` 改为和 `demo/segments.json` 一致。
- [x] TA5 `read_reports.py`：不再编造薄弱点（找不到报告输出 `[]`；读不到考纲或连不上 screenpipe 写 `[]` 并退出 1）；按窗口标题找 Kahoot 页并分页；按行找正确率 < 50% 的题，同分的知识点不标；整词匹配；不内置学科关键词；Windows 缺 `tzdata` 不再崩；新增 `--mock`；补了单元测试。
- [x] TA6 教案移到 `demo/lesson_plans/4A/2026-10-17.json`（`current_lesson.py` 找的位置）。
- [x] `demo/screenpipe_test_record.md` 补上没闭合的代码块，列出还没实测的项目。

还没做：

- [ ] TA1 实测：ocr、accessibility 的真实返回，`device_type` 大小写，`window_name` 是否按子串匹配，`Api(...)` 权限、`/notify`、溯源截图接口，以及 `deny` 规则到底作用在采集还是读取（清单见 `demo/screenpipe_test_record.md` 第 3 节）。实测后回来确认 `extract_segments.py`、`read_reports.py` 的解析。
- [ ] TA2 验收“在只读权限下运行”：要在演示电脑上用真实 pipe 跑一次。
- [ ] TA4 没有人工标注，也没有准确率数字。
- [ ] TA6 演示数据：T2 的教案和“上周”的课；录课、出题画面、Kahoot 报告页无法从仓库确认。
- [ ] TA7 `docs/DEMO.md` 的步骤、备用方案、彩排记录还是空的；备用录屏；两次彩排。

### 13.4 角色 B

已修（pipe 测试增加到 153 个）：

- [x] mock 课表不一致：`current_lesson.py --mock` 把“现在”固定为 2026-10-19 11:05（示例课表周一 10:00–11:00），`tools/seed_mock_home.py` 给那节课也写了教案；`pipe.md` 的 mock 说明加上了 `current_lesson.py`。本地 mock 跑第 0–7 步的脚本已验证能串起来。
- [x] `lookback.py` 判断麦克风改用 `extract_segments.is_mic()`（`device_type` 大小写不敏感）。（`style_inputs.py` 只读屏幕文字，不涉及。）
- [x] `check_quiz.py`：`source.quote` 超过 25 个词也会警告。
- [x] `pipe.md` 第 4 步改为“`read_reports.py` 退出码 1 时已写好 `[]`”；mock 说明加上 `read_reports.py --mock`（A 改的，B 已确认）。
- [x] `docs/SETUP.md` 第 5 步写明老师怎么启动控制台（虚拟环境 + `generate_cert.py` + `uvicorn`，按说明实测能启动），并说明第一次打开时的证书提示；时间改为 30–40 分钟，与测试卡一致。

还没做：

- [ ] TB2 没有 `pipe run chalkback` 让 agent 真正跑完一次、产出完整 outbox 的记录（要 screenpipe 和 AI 预设）。mock 模式下 `lookback.py` 不搜索，所有候选都变成“漏讲”——这是 mock 的设计，不是 bug。
- [ ] TB3 还没有用演示数据实际生成的 `quiz.json` 和 `game.html`。
- [ ] TB4 验收（区分“未讲”和“上周讲过”）需要真实录课数据（H6）。
- [ ] TB5 缺 T1、T2 两份明显不同的风格文件。
- [ ] TB6 实测：安装后 pipe 的名字（`chalkback` 还是 `pipe`）、`tree/main/pipe` 地址能否安装、`/notify` 的端口和请求体（`pipe/pipe.md` 里的 TODO）。
- [ ] TB7 新人测试没做，计时结果为空。
- [ ] 实测一次 pipe 运行时间低于 `timeout: 900`。
- [ ] 改 `pipe/scripts/build_game.py` 或 `check_quiz.normalize_answer` 时先告诉 C：控制台发布游戏和判分直接复用这两个函数（`console/app/contracts.py`）。

### 13.5 角色 C

已修（控制台测试从 8 个增加到 47 个，接口见 `console/README.md`）：

- [x] TC3：漏讲提醒按三类显示（未讲、以前讲过、Kahoot 薄弱点），知识点显示考纲标题；`/console` 不再回落到编造的假数据；上传前用 `coverage_share` schema 校验；重复共享替换本机旧记录（与 Hub 一致）。
- [x] TC4：不存在或未发布的 `quiz_id` 返回 404（以前 500）；填空题用 pipe 的 `normalize_answer` 判分；作答时间用 Europe/Paris。
- [x] TC2 `/setup` 的问题：必须明确 `consent: true`；Hub 不通时返回 502，不写 mock token；`workspace_id` 取自 join 的返回；拉取并缓存 `cache/syllabus.json`。
- [x] `/console` 不再依赖 Tailwind CDN 和 Google Fonts（内联 CSS，离线可用）。
- [x] 所有页面（包括 `/play`）只允许本机访问；`make teacher`、`make console` 绑定 `127.0.0.1`。
- [x] 补测试：`/review`、`/play`、`/shares`、`/setup` 及审核页。
- [x] 删除过期的 `verify_tc1.py`。
- [x] `console/README.md` 写明全部接口、作答接口和 `state/shares.json` 格式。
- [x] 证书私钥 `*.pem` 加入 `.gitignore`。

还没做：

- [ ] TC2 `/setup` 的 HTML 向导（现在 GET 返回 JSON）、学科和班级步骤、知情同意说明页。
- [ ] TC2 按课表写 pipe 定时（生成 cron，`POST /pipes/chalkback/config`）：要等 B 实测 pipe 安装后的名字（13.4 TB6）。
- [ ] TC3 出处显示截图：要等 A 实测截图接口（13.3 TA1）。
- [ ] TC6：`/shares` 合并 Hub 审计；`/style` 只返回 JSON，没有只读页面。
- [ ] 老师填写教案（`lesson_plan`）的入口；`config.auto_share` 没有用到。
- [ ] 准备一份多个昵称的全班 `attempts.jsonl` 演示数据（第 12 节）。

### 13.6 角色 D

已修（Hub 测试从 40 个增加到 50 个）：

- [x] Hub 默认是正式模式：不接受 `mock-token-*`，公开的 `DEMO-*` 邀请码失效（库里已有的也会删掉）；学校的邀请码用 `HUB_INVITES` 设置。`make hub` 和 `docker-compose.yml` 显式打开联调模式（`HUB_MOCK_AUTH=1`），`hub/Dockerfile` 不打开。
- [x] Hub 首页不再公开显示 `DEMO-*` 邀请码。
- [x] TD2 成员编号改为“已有最大编号 + 1”，两个人同时加入撞号时重算，不再返回 500。
- [x] TD4 `POST /api/coverage` 检查 `lesson_id` 里的老师是上传者本人、考纲版本已批准、知识点在那个版本里，否则 422。
- [x] `hub/generate_cert.py` 写到自己所在的目录；`make hub` 改为 `https://localhost:8000`，已在 macOS 上实测（`seed_demo.py` 也能跑通）。
- [x] 文档：`docs/ADMIN.md`、`hub/README.md` 的刷新间隔改为 3 秒，写明正式模式、`HUB_INVITES`、上传检查和公网证书；`README.md` 的 `make hub` 说明更新。

还没做：

- [ ] TD1 / H3 公网部署和地址（部署时设置 `HUB_INVITES`，不要设置 `HUB_MOCK_AUTH`，并配正式证书）。
- [ ] TD2 管理员没有页面可以创建工作区、轮换邀请码（现在只能改 `HUB_INVITES` 重启，旧码要手动从库里删）。
- [ ] 考纲版本号和“当前考纲”按考纲 / 工作区全局计算：一所学校、一个学科没问题，多工作区或多学科要改表结构。
- [ ] TD7 幻灯片（开场页、架构图、商业模式、隐私边界）不在仓库里，状态未知。

### 13.7 去掉手机端、改用 HTTPS 后要同步的地方

团队已决定：学生游戏只在老师电脑上的浏览器里打开，不做手机端；控制台和 Hub 都用 HTTPS。

- [x] 控制台代码、测试、`Makefile`、`console/README.md`、`README.md`、`docker-compose.yml` 已改。（C）
- [x] 本文档已改为本机游戏和 HTTPS：第 2 节、第 3 节第 7–8 步、第 6.3 节、第 6.4 节、第 8 节 TB3 / TC4 / TD1、第 10 节第 3 条、第 11 节 0:00 和 1:10 两行、第 12 节对应风险。（全员）
- [x] `docs/SETUP.md`（二维码、手机、热点）、`pipe/prompts/gen_quiz.md`（“用手机作答”“手机一屏”）、`pipe/templates/game.html`（不引用外部资源的理由改为离线可用）。（B）
- [x] `docs/DEMO.md` 的手机连接检查项改为本机游戏和全班作答数据。（A）
- [x] http 改 https：`pipe/pipe.md` 的通知链接、`pipe/scripts/doctor.py`、`docs/SETUP.md`。（B）

### 13.8 本文档自身

- [ ] 第 2 节架构图导出时丢失（`&#91;embedded content…`），可改为引用仓库里的 `工作流.webp`。
- [ ] 第 6.1 节的 frontmatter 和步骤与 `pipe/pipe.md` 不一致：缺 `Api(...)` 权限、第 0 步 `doctor.py`、第 1 步 `current_lesson.py`、`read_reports.py` 的参数；`game.html` 实际是把去掉答案的题目嵌入页面，不是读取 `quiz.json`。
- [ ] 第 6.2 节缺 `work/{lesson_id}/` 和 `state/kp_stats/` 的存放位置；第 5 节契约表缺 `config`；第 5 节 `weights` 示例里 KP03 按规则应为 2.5。
- [ ] 第 7 节仓库结构缺 `pipe/schemas/`、`pipe/tests/`、其余脚本、`tools/`、`tests/`、`Makefile`、`docker-compose.yml`。
- [ ] 第 0 节“完成的定义”加上 `make check` 通过；“第 3 小时前”统一成具体时间。
