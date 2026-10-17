"""SQLite 存储（TD2–TD5）。只保存批准上传的数据：工作区、成员、考纲版本、coverage_share、审计日志。

HUB_DB 环境变量指定数据库文件，默认 hub/chalkback.db（已 gitignore）。
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("HUB_DB", Path(__file__).resolve().parents[1] / "chalkback.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
  workspace_id TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  exam_date    TEXT                        -- 考前预警用（§6.4）
);
CREATE TABLE IF NOT EXISTS invites (
  invite_code  TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces
);
CREATE TABLE IF NOT EXISTS members (
  member_id    TEXT PRIMARY KEY,           -- teacher_id 等
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  display_name TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('teacher', 'head', 'admin')),
  token        TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS syllabi (
  syllabus_id  TEXT NOT NULL,
  version      INTEGER NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('draft', 'approved')),
  body         TEXT NOT NULL,              -- syllabus JSON
  PRIMARY KEY (syllabus_id, version)
);
CREATE TABLE IF NOT EXISTS coverage_shares (
  share_id     TEXT PRIMARY KEY,
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


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
