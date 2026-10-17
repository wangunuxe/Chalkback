"""SQLite storage (TD2-TD5). Stores only data whose upload was approved: workspaces, members, syllabus versions, coverage_share, audit log.

The HUB_DB environment variable sets the database file; default hub/chalkback.db (gitignored).
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
  exam_date    TEXT                        -- used for pre-exam alerts (§6.4)
);
CREATE TABLE IF NOT EXISTS invites (
  invite_code  TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  role         TEXT NOT NULL CHECK (role IN ('teacher', 'head', 'admin'))  -- one code per role
);
CREATE TABLE IF NOT EXISTS members (
  member_id    TEXT PRIMARY KEY,           -- teacher_id etc.
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
  approved_at  TEXT,                       -- when the department head approved it (A4)
  PRIMARY KEY (syllabus_id, version)
);
CREATE TABLE IF NOT EXISTS coverage_shares (
  share_id     TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces,
  teacher_id   TEXT NOT NULL REFERENCES members(member_id),
  lesson_id    TEXT NOT NULL,
  class_id     TEXT NOT NULL,
  body         TEXT NOT NULL,              -- JSON already validated against the coverage_share schema
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


# Demo workspace: §6.4 has no "create workspace" endpoint, so the Hub creates it on startup (TD2).
DEMO_WORKSPACE = ("W1", "Collège Démo", "2026-12-18")  # exam date: no settings endpoint is defined; HUB_EXAM_DATE can override it (TD6)
# The public demo invite codes only work in test mode (HUB_MOCK_AUTH=1); they are in the repo, so on the public internet anyone could use them to join as admin.
DEMO_INVITES = {"DEMO-TEACHER": "teacher", "DEMO-HEAD": "head", "DEMO-ADMIN": "admin"}
# Demo syllabus v1 (approved), used by A/B/C until a department head uploads a new version. Replace with the files in demo/syllabus/ once H4 is finalized.
DEMO_SYLLABUS = EXAMPLES / "syllabus.json"


def invite_codes() -> dict[str, str]:
    """Invite code -> role. HUB_INVITES="teacher=code1,head=code2,admin=code3" sets the school's own codes;
    if unset, the public DEMO-* codes are used only in test mode; otherwise there are no codes at all (nobody can join, which reminds the admin to set them)."""
    from .auth import mock_auth_enabled

    configured = os.environ.get("HUB_INVITES", "").strip()
    if configured:
        codes = {}
        for pair in configured.split(","):
            role, _, code = pair.strip().partition("=")
            if role not in ("teacher", "head", "admin") or not code.strip():
                raise ValueError(f"HUB_INVITES should look like teacher=code,head=code,admin=code; could not parse: {pair!r}")
            codes[code.strip()] = role
        return codes
    return dict(DEMO_INVITES) if mock_auth_enabled() else {}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    with conn:
        conn.execute("INSERT OR IGNORE INTO workspaces (workspace_id, name, exam_date) VALUES (?, ?, ?)", DEMO_WORKSPACE)
        codes = invite_codes()
        # DEMO-* codes written to the database earlier in test mode must stop working after switching to production mode
        stale = [code for code in DEMO_INVITES if code not in codes]
        conn.executemany("DELETE FROM invites WHERE invite_code = ?", [(code,) for code in stale])
        conn.executemany(
            "INSERT OR IGNORE INTO invites (invite_code, workspace_id, role) VALUES (?, ?, ?)",
            [(code, DEMO_WORKSPACE[0], role) for code, role in codes.items()],
        )
        syllabus = json.loads(DEMO_SYLLABUS.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR IGNORE INTO syllabi (workspace_id, syllabus_id, version, status, body, approved_at)"
            " VALUES (?, ?, ?, 'approved', ?, '2026-10-17T00:00:00+00:00')",
            (DEMO_WORKSPACE[0], syllabus["syllabus_id"], syllabus["version"], json.dumps(syllabus, ensure_ascii=False)),
        )
    return conn
