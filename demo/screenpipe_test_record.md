# TA1 test log: screenpipe local API and permission configuration

**Recorded by**: role A (Aurora)  
**Time**: 2026-10-17T12:15:00+02:00  
**Test environment**:
- Demo machine 1 (T1): macOS Sonoma 14.5 (Apple Silicon), screenpipe desktop v0.2.x
- Demo machine 2 (T2): Windows 11 (23H2), screenpipe desktop v0.2.x

---

## 1. Permission and authentication findings

1. **Auth header**:
   - When screenpipe starts a pipe, it automatically injects the env var `$SCREENPIPE_LOCAL_API_KEY` into the execution environment.
   - Every request to the local port `http://localhost:3030` must include:
     `Authorization: Bearer $SCREENPIPE_LOCAL_API_KEY`.
2. **Read-only permission boundary**:
   - The official reader preset only allows basic query endpoints such as `GET /search` and `GET /health`.
   - **Do not call `/raw_sql`**: with read-only permissions, calling `/raw_sql` returns `403 Forbidden` directly. The whole team extracts data with `GET /search` only.
3. **Privacy denylist test**:
   - When `deny` rules are configured in `pipe.md` (e.g. 1Password, window titles containing incognito/privée), screenpipe's local capture service drops the data at the capture layer, and `/search` returns no matches, so sensitive information never leaves the capture source.

---

## 2. API test: GET /search

### 2.1 Microphone audio transcript extraction

- **Endpoint**: `GET http://localhost:3030/search`
- **Query parameters**:
  - `content_type=audio`
  - `start_time=2026-10-17T10:00:00+02:00` (ISO 8601 with timezone)
  - `end_time=2026-10-17T11:00:00+02:00`
  - `limit=50`
  - `offset=0`
- **Key filter rule**:
  - Must filter on `device_type == "input"` to **keep only the teacher's own microphone speech**, excluding sound played by the computer (output).
- **Actual response structure**:
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
```

---

## 3. Not yet tested (TA1 not done; put results in `screenpipe_probe/README.md`)

Only audio is covered above. A's scripts currently parse the items below leniently; come back and confirm after testing:

- [ ] Real response for `content_type=ocr` (field names `frame_id`, `app_name`, `window_name`)
- [ ] Whether `content_type=accessibility` is supported, plus its `type` and field names (`extract_segments.py` accepts `UI` / `Accessibility`)
- [ ] Case of `device_type` (`input` or `Input`); when `device_type` is absent, whether `device_name` ends with `(input)`
- [ ] Whether the `window_name` parameter matches by substring (`read_reports.py` uses it to find the Kahoot window)
- [ ] Whether timestamps are UTC (`Z`) or a local offset (the scripts handle both and convert to Europe/Paris)
- [ ] pipe permissions: whether `Api(GET /search)` and `Api(POST /notify)` are allowed; whether `/raw_sql` is denied
- [ ] Source screenshot API (needed for the console to show source screenshots)
- [ ] Reconfirm section 1, item 3: does the `deny` rule limit what the pipe can read, or does screenpipe not capture at all? The privacy statement is worded differently for each.
