"""SQLite 存储（TD2–TD5）。只保存批准上传的数据：工作区、成员、考纲版本、coverage_share、审计日志。

HUB_DB 环境变量指定数据库文件，默认 hub/chalkback.db（已 gitignore）。
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .mock import EXAMPLES

DB_PATH = Path(os.environ.get("HUB_DB", Path(__file__).resolve().parents[1] / "chalkback.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
  workspace_id TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  exam_date    TEXT                        -- 考前预警用（§6.4）
);
CREATE TABLE IF NOT EXISTS invites (
  invite_code  TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  role         TEXT NOT NULL CHECK (role IN ('teacher', 'head', 'admin'))  -- 每种角色一个码
);
CREATE TABLE IF NOT EXISTS members (
  member_id    TEXT PRIMARY KEY,           -- teacher_id 等
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  display_name TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('teacher', 'head', 'admin')),
  token        TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS syllabi (
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  syllabus_id  TEXT NOT NULL,
  version      INTEGER NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('draft', 'approved')),
  body         TEXT NOT NULL,              -- syllabus JSON
  approved_at  TEXT,                       -- 组长批准时间（A4）
  PRIMARY KEY (syllabus_id, version)
);
CREATE TABLE IF NOT EXISTS coverage_shares (
  share_id     TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  teacher_id   TEXT NOT NULL REFERENCES members(member_id),
  lesson_id    TEXT NOT NULL,
  class_id     TEXT NOT NULL,
  body         TEXT NOT NULL,              -- 已通过 coverage_share schema 校验的 JSON
  shared_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  event_id     TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  actor_role   TEXT NOT NULL,
  actor_id     TEXT NOT NULL,
  action       TEXT NOT NULL,
  target_id    TEXT NOT NULL,
  at           TEXT NOT NULL
);
"""


# 演示工作区：§6.4 没有“创建工作区”的接口，Hub 启动时自动建好（TD2）。
DEMO_WORKSPACE = ("W1", "Collège Démo")
DEMO_INVITES = {"DEMO-TEACHER": "teacher", "DEMO-HEAD": "head", "DEMO-ADMIN": "admin"}
# 演示考纲 v1（已批准），在组长上传新版本之前供 A/B/C 使用。H4 定稿后换成 demo/syllabus/ 里的文件。
DEMO_SYLLABUS = EXAMPLES / "syllabus.json"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    with conn:
        conn.execute("INSERT OR IGNORE INTO workspaces (workspace_id, name) VALUES (?, ?)", DEMO_WORKSPACE)
        conn.executemany(
            "INSERT OR IGNORE INTO invites (invite_code, workspace_id, role) VALUES (?, ?, ?)",
            [(code, DEMO_WORKSPACE[0], role) for code, role in DEMO_INVITES.items()],
        )
        syllabus = json.loads(DEMO_SYLLABUS.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR IGNORE INTO syllabi (workspace_id, syllabus_id, version, status, body, approved_at)"
            " VALUES (?, ?, ?, 'approved', ?, '2026-10-17T00:00:00+00:00')",
            (DEMO_WORKSPACE[0], syllabus["syllabus_id"], syllabus["version"], json.dumps(syllabus, ensure_ascii=False)),
        )
    return conn
