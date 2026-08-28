# 56. Parallel Leverage

$$
\Pi_I
=
\frac{W_I}{D_I}.
$$

Run Summary 可輸出：

```text
interaction_work
interaction_depth
structural_parallelism
```

---

# 57. Human Intervention Density

$$
\rho_H
=
\frac{
N_{\mathrm{human\ checkpoints}}
}{
N_{\mathrm{effective\ transitions}}
}.
$$

MVP 可使用：

```text
human.checkpoint.resolved count
/
action.completed + validation.completed + commit.confirmed
```

作簡化 proxy。

---

# 58. Delegation Span

保存：

```text
human_checkpoint_prev
human_checkpoint_next
events_between
depth_between
wall_time_between
```

因此可以比較：

$$
\text{Delegation Duration}
\neq
\text{Delegation Depth}.
$$

---

# 59. Quality-Adjusted Completion

Run Summary 可輸出：

$$
QAC
=
Q_{\mathrm{completion}}
Q_{\mathrm{verification}}
Q_{\mathrm{result}}.
$$

若有 hard gate：

$$
QAC_{eff}
=
G_{hard}QAC.
$$

---

# 60. Historical Sedimentation

ATL 的最終 world layer：

```text
commit.confirmed
```

可以再被更上層 civilization/history service 吸收。

ITR 只負責產生：

```text
verified commit receipt
```

不自行宣稱某 commit 具有巨大歷史價值。

---

# 61. Privacy

預設禁止在 ledger 直接保存：

- full hidden reasoning；
- raw secrets；
- passwords；
- unrestricted private memory；
- unnecessary personal data。

應優先：

```text
reference
digest
redacted summary
typed state
```

---

# 62. Content Capture Policy

OpenTelemetry GenAI conventions 對 prompt / completion content 的 capture 也需要 opt-in / privacy consideration。

ITR v0.1 原則：

$$
\boxed{
\text{Observability}
\neq
\text{Collect Everything}.
}
$$

---

# 63. Authority / Audit Separation

Audit record：

```text
what happened
```

Authority record：

```text
who was allowed to cause it
```

兩者不同。

因此：

$$
\boxed{
\text{Observed}
\neq
\text{Authorized}.
}
$$

---

# 64. Minimum Production Gates

高風險 external commit 前至少檢查：

```text
intent_version current
hard constraints preserved
authority valid
required validation passed
budget within ceiling
external target confirmed
idempotency / reconciliation available
commit receipt enabled
```

---

# 65. MVP Directory Layout

```text
interaction_time_runtime/
├── whitepaper.md
├── schemas/
│   ├── intent.schema.json
│   ├── run.schema.json
│   ├── temporal-event.schema.json
│   ├── checkpoint.schema.json
│   ├── commit-receipt.schema.json
│   └── run-summary.schema.json
├── examples/
│   ├── demo_run.events.jsonl
│   └── demo_run.summary.json
├── sql/
│   └── sqlite_schema.sql
├── validator/
│   └── validate_pack.py
├── VALIDATION.json
└── SHA256SUMS.txt
```

---

# 66. v0.1 Demo Scenario

範例：

```text
User intent
→ Plan
→ Agent builds artifact
→ Validator fails
→ Retry
→ Validator passes
→ Human approval requested
→ Run suspended
→ Human approves
→ Run resumed
→ External commit
→ Commit confirmation
→ Run succeeds
```

這個例子故意包含：

- retry；
- validation；
- human checkpoint；
- suspend/resume；
- world commit。

用來驗證 ledger 是否真的跨越前八篇所有主要層。

---

# 67. Demo Causal Graph

$$
e_1
\rightarrow
e_2
\rightarrow
e_3
\rightarrow
e_4
\rightarrow
e_5
\rightarrow
e_6
\rightarrow
e_7
\rightarrow
e_8
\rightarrow
e_9.
$$

未來 multi-agent demo 應加入：

$$
e_a
\parallel
e_b
\rightarrow
e_{join}.
$$

v0.1 schema 已支援多 parent，但 sample 保持最小可讀。

---

# 68. Reference Metrics

Run Summary 第一版可計：

```text
event_count
action_count
validation_count
retry_count
human_checkpoint_count
machine_runtime_ms
human_governance_ms
token_in
token_out
tool_calls
nominal_completion
verified_completion
interaction_work
interaction_depth
human_intervention_density
commit_state
```

---

# 69. Failure Semantics

`run.failed` MUST 有：

```text
failure_class
failure_origin_event?
surface_failure_event?
recoverable
```

建議 failure class：

```text
intent
specification
plan
executor
tool
observation
constraint
validation
budget
authority
state
external
unknown
```

---

# 70. False Completion Guard

若：

```text
agent_claims_done = true
```

但：

```text
verified_completion < required_completion
```

系統 MUST NOT 將 Run 標為：

```text
succeeded
```

而應：

```text
validating
failed
partial
```

依 contract 決定。

---

# 71. Scheduler Interface

ITR 不規定 scheduler algorithm。

只要求 scheduler emit：

```text
task.ready
action.started
action.completed
action.failed
```

並保存 causal dependency。

因此可接：

- serial；
- DAG；
- multi-agent；
- distributed worker；
- workflow engine。

---

# 72. Dynamic Graph

若 runtime 新增 dependency / branch：

```text
graph.revision
```

必須成為 ledger event。

不能 silent mutate。

---

# 73. Soft Dependency

未來 v0.2 可加入：

```text
dependency_type:
  hard
  soft
  evidence
  authority
  commit
```

v0.1 `causal_parent_ids` 只表示 canonical hard happens-before。

---

# 74. Event Projection

同一 ATL event 可投影到：

- OpenTelemetry span；
- CloudEvent；
- UI timeline；
- Mermaid DAG；
- PHOSPHOR；
- SQL analytics；
- audit report。

因此 Ledger 是 canonical semantic core，不是 UI。

---

# 75. CLI 草案

```bash
itr init run.json
itr append event.json
itr replay RUN_ID
itr status RUN_ID
itr graph RUN_ID
itr budget RUN_ID
itr quality RUN_ID
itr checkpoints RUN_ID
itr commit RUN_ID
itr verify-pack .
```

v0.1 本包不提供完整 CLI，只提供 validator。

---

# 76. HTTP API 草案

```text
POST /runs
POST /runs/{id}/events
GET  /runs/{id}
GET  /runs/{id}/events
GET  /runs/{id}/graph
GET  /runs/{id}/summary
POST /runs/{id}/checkpoints
POST /runs/{id}/resume
POST /runs/{id}/commit
```

---

# 77. Adapter Contract

Runtime adapter 至少提供：

```text
emit_event(event)
store_artifact(bytes, metadata)
load_artifact(ref)
create_checkpoint(state)
resolve_authority(ref)
validate(subject)
commit(candidate)
reconcile(commit)
```

---

# 78. Event Store Contract

```text
append(event) -> ledger_seq
read_run(run_id) -> events[]
read_from(run_id, seq) -> events[]
```

MUST:

- append-only；
- preserve order；
- reject duplicate event_id；
- reject malformed event；
- not silently rewrite payload。

---

# 79. Artifact Store Contract

```text
put(bytes) -> sha256 ref
get(ref) -> bytes
verify(ref) -> bool
```

---

# 80. Validator Contract

```text
validate(subject_ref, contract_ref)
→ ValidationRecord
```

ValidationRecord MUST 可持久化。

---

