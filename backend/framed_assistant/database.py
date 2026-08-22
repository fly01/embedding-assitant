from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS conversations_scope ON conversations(actor_id, scope_key, status);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  visible_at TEXT,
  completed_at TEXT,
  edited_at TEXT,
  UNIQUE(conversation_id, sequence)
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  input_message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  provider TEXT NOT NULL,
  usage TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  scope_kind TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  conversation_id TEXT,
  run_id TEXT,
  type TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(scope_kind, scope_id, seq)
);

CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
  actor_id TEXT NOT NULL,
  owner_scope TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  source TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  upload_status TEXT NOT NULL,
  processing_status TEXT NOT NULL,
  retention_policy TEXT NOT NULL,
  permission_scope TEXT NOT NULL,
  metadata TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachment_results (
  id TEXT PRIMARY KEY,
  attachment_id TEXT NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
  processor TEXT NOT NULL,
  processor_version TEXT NOT NULL,
  status TEXT NOT NULL,
  result TEXT NOT NULL,
  warnings TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcripts (
  id TEXT PRIMARY KEY,
  attachment_id TEXT NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  language TEXT NOT NULL,
  adapter TEXT NOT NULL,
  revision INTEGER NOT NULL,
  is_user_correction INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(attachment_id, revision)
);

CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  run_id TEXT,
  action_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  state TEXT NOT NULL,
  execution_mode TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  policy_decision TEXT,
  result TEXT,
  plugin_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
  scope TEXT NOT NULL,
  content TEXT NOT NULL,
  provenance TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_artifacts (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  profile TEXT NOT NULL,
  kind TEXT NOT NULL,
  source_revision INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  source_url TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS privacy_jobs (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  scope TEXT NOT NULL,
  preview TEXT NOT NULL,
  results TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plugins (
  id TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  protocol_range TEXT NOT NULL,
  data_schema_version TEXT NOT NULL,
  enabled INTEGER NOT NULL,
  capabilities TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS host_records (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  title TEXT NOT NULL,
  amount REAL NOT NULL,
  occurred_at TEXT NOT NULL,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS host_links (
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  PRIMARY KEY(source_id, target_id)
);

CREATE TABLE IF NOT EXISTS attachment_promotions (
  id TEXT PRIMARY KEY,
  attachment_id TEXT REFERENCES attachments(id) ON DELETE SET NULL,
  host_record_id TEXT NOT NULL REFERENCES host_records(id) ON DELETE CASCADE,
  actor_id TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS attachment_promotion_identity
ON attachment_promotions(attachment_id, host_record_id);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  operation TEXT NOT NULL,
  decision TEXT NOT NULL,
  metadata TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()
