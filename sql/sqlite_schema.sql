-- Interaction-Time Runtime & Agent Temporal Ledger v0.1
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  intent_id TEXT NOT NULL,
  intent_version INTEGER NOT NULL,
  plan_id TEXT NOT NULL,
  plan_version INTEGER NOT NULL,
  runtime_id TEXT NOT NULL,
  executor_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  run_id TEXT NOT NULL,
  ledger_seq INTEGER NOT NULL,
  event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  attempt_id TEXT,
  loop_id TEXT,
  actor_id TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (run_id, ledger_seq),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN
  SELECT RAISE(ABORT, 'ATL events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN
  SELECT RAISE(ABORT, 'ATL events are append-only');
END;

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  media_type TEXT NOT NULL,
  byte_size INTEGER,
  uri TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  event_offset INTEGER NOT NULL,
  state_ref TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS validations (
  validation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  subject_ref TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS commits (
  commit_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  state TEXT NOT NULL,
  target TEXT NOT NULL,
  authority_ref TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  executed_at TEXT,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_events_run_type ON events(run_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor_id, actor_type);
CREATE INDEX IF NOT EXISTS idx_commits_run ON commits(run_id);
