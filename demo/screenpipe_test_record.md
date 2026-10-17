# TA1 实测记录：screenpipe 本地 API 与权限配置规范

**记录人**：角色 A (Aurora)  
**时间**：2026-10-17T12:15:00+02:00  
**测试环境**：
- 演示机 1 (T1)：macOS Sonoma 14.5 (Apple Silicon), screenpipe desktop v0.2.x
- 演示机 2 (T2)：Windows 11 (23H2), screenpipe desktop v0.2.x

---

## 1. 权限与认证规则结论

1. **认证 Header**：
   - screenpipe 启动 pipe 时，会自动在执行环境注入环境变量 `$SCREENPIPE_LOCAL_API_KEY`。
   - 所有调用本地端口 `http://localhost:3030` 的请求必须附带：
     `Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY`。
2. **只读权限边界**：
   - 官方 reader 预设只放行 `GET /search`、`GET /health` 等基础查询端点。
   - **禁止调用 `/raw_sql`**：只读权限下调用 `/raw_sql` 会直接返回 `403 Forbidden`。全队数据提取一律使用 `GET /search`。
3. **隐私黑名单实测**：
   - 在 `pipe.md` 中配置 `deny` 规则（如 1Password、包含 incognito/privée 的窗口标题）时，screenpipe 本地抓取服务直接在采集层丢弃数据，`/search` 无法查到任何匹配项，保障敏感信息不出采集源。

---

## 2. 接口实测：GET /search

### 2.1 音频麦克风转写提取

- **请求端点**：`GET http://localhost:3030/search`
- **查询参数**：
  - `content_type=audio`
  - `start_time=2026-10-17T10:00:00+02:00`（ISO 8601 带时区）
  - `end_time=2026-10-17T11:00:00+02:00`
  - `limit=50`
  - `offset=0`
- **关键过滤规则**：
  - 必须过滤 `device_type == "input"`，以**仅保留老师本人的麦克风发言**，排除电脑系统播放的声音（output）。
- **实测返回结构**：
```json
{
  "data": [
    {
      "type": "Audio",
      "content": {
        "audio_transcription_id": 812,
        "transcription": "Alors aujourd'hui nous allons aborder le passé composé avec l'auxiliaire avoir.",
        "timestamp": "2026-10-17T10:12:05+02:00",
        "audio_chunk_id": 401,
        "offset_index": 0,
        "device": "MacBook Pro Microphone",
        "device_type": "input",
        "speaker": null
      }
    },
    {
      "type": "Audio",
      "content": {
        "audio_transcription_id": 813,
        "transcription": "Faites attention aux participes passés réguliers du premier groupe.",
        "timestamp": "2026-10-17T10:12:35+02:00",
        "audio_chunk_id": 402,
        "offset_index": 1,
        "device": "MacBook Pro Microphone",
        "device_type": "input",
        "speaker": null
      }
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 2
  }
}