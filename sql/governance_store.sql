-- CTCL-ITR v0.2.4 Durable Governance Store reference schema
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;

CREATE TABLE IF NOT EXISTS governance_approval_requests (
  approval_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  status TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  state_version INTEGER NOT NULL DEFAULT 1,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_decision_receipts (
  decision_id TEXT PRIMARY KEY,
  approval_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (approval_id) REFERENCES governance_approval_requests(approval_id)
);

CREATE TABLE IF NOT EXISTS governance_authority_grants (
  authority_ref TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  principal TEXT NOT NULL,
  state TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  uses INTEGER NOT NULL,
  max_uses INTEGER NOT NULL,
  state_version INTEGER NOT NULL DEFAULT 1,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (decision_id) REFERENCES governance_decision_receipts(decision_id)
);

CREATE TABLE IF NOT EXISTS governance_mutations (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  mutation_type TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_governance_request_status
ON governance_approval_requests(status, requested_at, approval_id);
CREATE INDEX IF NOT EXISTS idx_governance_receipt_approval
ON governance_decision_receipts(approval_id);
CREATE INDEX IF NOT EXISTS idx_governance_grant_decision
ON governance_authority_grants(decision_id);

CREATE TRIGGER IF NOT EXISTS governance_mutations_no_update
BEFORE UPDATE ON governance_mutations
BEGIN
  SELECT RAISE(ABORT, 'governance mutation journal is append-only');
END;

CREATE TRIGGER IF NOT EXISTS governance_mutations_no_delete
BEFORE DELETE ON governance_mutations
BEGIN
  SELECT RAISE(ABORT, 'governance mutation journal is append-only');
END;
