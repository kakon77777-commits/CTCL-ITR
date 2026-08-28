# 26. Validation

ValidationRecord：

```text
validation_id
validator_id
subject_ref
status
score?
coverage?
independence?
evidence_refs[]
required_actions[]
created_at
```

v0.1 status：

```text
pass
fail
partial
blocked
not_applicable
```

---

# 27. Completion

Completion 與 validation 分開。

```json
"completion": {
  "nominal": 0.9,
  "verified": 0.6,
  "criteria_met": 3,
  "criteria_total": 4
}
```

因此：

$$
\boxed{
\text{Completed}
\neq
\text{Verified}.
}
$$

---

# 28. Quality Vector

Run Summary 可保存：

```json
"quality": {
  "intent": 0.98,
  "specification": 0.95,
  "plan": 0.90,
  "execution": 0.87,
  "constraint_retention": 1.0,
  "verification": 0.92,
  "completion": 1.0,
  "result": 0.95,
  "governance": 1.0,
  "world_commit": 1.0
}
```

不要求每 event 都有完整品質向量。

Event 可只記：

```text
quality_delta
```

或 evaluator output ref。

---

# 29. Human Checkpoint

Human checkpoint 不是普通 tool call。

事件：

```text
human.checkpoint.requested
human.checkpoint.resolved
```

Data SHOULD 包含：

```text
trigger
decision_required
options[]
risk_summary
authority_needed
decision
human_active_ms
```

---

# 30. Decision-Ready State

對 human checkpoint，不應直接丟完整 trace。

應提供：

```text
intent
current_state
why_now
options
evidence
risk
recommended_action
authority_needed
rollback_state
```

這降低 context reconstruction cost。

---

# 31. Retry

Retry MUST 引用：

```text
retry_of
attempt_id
error_class
```

事件：

```text
retry.scheduled
retry.started
retry.completed
retry.exhausted
```

Retry 不等於 Replan。

---

# 32. Replan

Replan MUST 建立：

```text
plan_version + 1
```

並記：

```text
replan.reason
replan.from_plan
replan.to_plan
```

原 plan 不可覆寫。

---

# 33. Recovery

Recovery event：

```text
recovery.started
recovery.restored
recovery.failed
```

Data：

```text
recovery_type
checkpoint_ref
invalidated_events[]
invalidated_artifacts[]
```

---

# 34. Compensation

Compensation MUST 形成新歷史。

```text
compensation.started
compensation.completed
```

不可刪除原 external action event。

因此：

$$
\boxed{
\text{Compensation}
\neq
\text{History Erasure}.
}
$$

---

# 35. Checkpoint

Checkpoint 是：

```text
checkpoint_id
run_id
event_offset
state_ref
artifact_refs[]
authority_ref?
budget_snapshot?
created_at
```

Checkpoint 不一定把所有 bytes 複製一份。

可以只是：

$$
(EventOffset,StateRef,ArtifactRefs).
$$

---

# 36. Suspend / Resume

`run.suspended` MUST 有 reason：

```text
waiting_for_human
waiting_for_event
waiting_for_agent
budget_pause
external_dependency
manual_pause
```

Resume MUST 重新驗證：

```text
authority
condition
artifact validity
external state
executor version
```

不能直接從舊 memory 盲跑。

---

# 37. Wake Rules

ITR 可直接採 Temporal Loop 類型：

```text
delay
interval
datetime
event
webhook
human_decision
agent_signal
condition_poll
```

Wake 是 scheduler concern；ATL 只記 registration / firing / resolution。

---

# 38. Event Type Namespace

v0.1 建議：

```text
intent.*
plan.*
run.*
attempt.*
loop.*
action.*
observation.*
tool.*
artifact.*
validation.*
quality.*
budget.*
authority.*
human.*
retry.*
replan.*
recovery.*
checkpoint.*
compensation.*
commit.*
world.*
```

---

# 39. v0.1 核心 Event Types

最低核心：

```text
intent.accepted
plan.created

run.created
run.started
run.suspended
run.resumed
run.validating
run.succeeded
run.failed
run.cancelled

attempt.started
attempt.failed
attempt.succeeded

loop.started
loop.suspended
loop.woken
loop.resumed
loop.completed
loop.timeout

action.proposed
action.started
action.completed
action.failed
observation.recorded

artifact.created

validation.started
validation.completed

budget.consumed
budget.exceeded

authority.checked
authority.expired
authority.denied

human.checkpoint.requested
human.checkpoint.resolved

retry.scheduled
replan.created
recovery.started
recovery.completed

checkpoint.created

commit.proposed
commit.authorized
commit.executed
commit.confirmed
commit.failed
commit.compensated
```

---

# 40. Event Hashing

v0.1 MAY 保存：

```text
event_digest
previous_ledger_digest
```

形成簡單 hash chain：

$$
h_n
=
H(
serialize(e_n)
\parallel
h_{n-1}
).
$$

這不是 blockchain。

用途是：

- accidental corruption detection；
- append-only audit；
- export integrity。

---

# 41. Event Ordering

Ledger storage MUST 有：

```text
ledger_seq
```

對單一 Run 單調增加。

但：

$$
ledger\_seq
$$

只是紀錄順序。

它不等於：

$$
causal\_order.
$$

因此：

$$
\boxed{
\text{Storage Order}
\neq
\text{Causal Order}.
}
$$

---

# 42. Distributed Trace Mapping

ITR SHOULD 支援：

```text
trace_id
span_id
traceparent
tracestate
```

但它們是 observability correlation。

ITR causal DAG 仍以：

```text
causal_parent_ids[]
```

為 canonical temporal relation。

---

# 43. W3C Trace Context

跨 HTTP / service boundary 時可傳播：

```text
traceparent
tracestate
```

ITR 可把：

```text
run_id
event_id
```

與 trace / span 關聯。

但不把 `tracestate` 當 authority 或 intent carrier。

---

# 44. OpenTelemetry GenAI Mapping

截至本文件日期，OpenTelemetry GenAI conventions 已有 Agent / GenAI operation，例如：

```text
invoke_agent
plan
execute_tool
retrieval
search_memory
update_memory
```

ITR 可映射：

```text
ITR action.started
→ OTel span start

ITR action.completed
→ OTel span end

ITR tool execution
→ gen_ai.operation.name = execute_tool

ITR agent invocation
→ gen_ai.operation.name = invoke_agent

ITR planning
→ gen_ai.operation.name = plan
```

OTel 用來觀測 latency / token / operation。

ATL 額外保存：

- intent version；
- authority；
- human governance time；
- quality；
- completion；
- world commit；
- causal multi-parent join。

---

# 45. OpenTelemetry Span Tree 不足之處

普通 trace 常使用：

$$
parent(span)
$$

單父樹。

Agent 執行可能：

$$
A
\parallel
B
\rightarrow
Join.
$$

Join 有：

$$
Parents(Join)=\{A,B\}.
$$

因此 ATL 需要 explicit multi-parent causality。

對 OTel exporter，可使用：

- parent span；
- span links；
- attributes；

投影，但不能丟失 canonical DAG。

---

# 46. CloudEvents-Compatible Delivery

ITR event 可以包成 CloudEvents：

```json
{
  "specversion": "1.0",
  "id": "evt-...",
  "source": "/itr/run/demo-001",
  "type": "org.evemiss.itr.action.completed",
  "subject": "run/demo-001/action/build",
  "time": "2026-08-20T02:00:00+08:00",
  "datacontenttype": "application/json",
  "data": {
    "...": "ITR TemporalEvent"
  }
}
```

CloudEvents 是 transport envelope。

ATL schema 才是 domain semantics。

---

# 47. JSON Schema

所有 v0.1 canonical JSON 使用：

```text
JSON Schema Draft 2020-12
```

本包附：

```text
schemas/intent.schema.json
schemas/run.schema.json
schemas/temporal-event.schema.json
schemas/checkpoint.schema.json
schemas/commit-receipt.schema.json
schemas/run-summary.schema.json
```

---

# 48. SQLite Storage Model

v0.1 reference DDL 提供：

```text
runs
events
artifacts
checkpoints
validations
commits
```

Events MUST append-only。

Reference SQLite 使用 trigger 拒絕：

```text
UPDATE events
DELETE FROM events
```

---

# 49. Event Replay

Current Run State：

$$
S_n
=
fold(S_0,e_1,\ldots,e_n).
$$

因此：

```text
state.json
```

可以作 materialized projection，但不是 canonical history。

---

# 50. Exactly-Once 警告

ITR/ATL 不宣稱 external action exactly-once。

如果 process crash 發生在：

```text
action executed
↓
crash
↓
ledger not updated
```

系統無法只靠本地 ledger 知道世界是否已變。

因此外部 executor 需要：

- idempotency key；
- external receipt；
- reconciliation；
- compensation。

---

# 51. Execution Key

建議：

$$
execution\_key
=
H(
IntentVersion,
ActionContract,
InputArtifacts,
ExecutorVersion
).
$$

它不等於 Event ID。

Event ID 每次 attempt 不同。

Execution key 可以跨 retry 保持穩定。

---

# 52. Reconciliation

對 uncertain external action，建立：

```text
commit.reconcile_requested
commit.reconciled
```

讀取外部 reality：

```text
payment state
message delivery
deployment state
database version
```

再決定：

```text
confirmed
not_executed
conflicted
unknown
```

---

# 53. Temporal Ledger Queries

MVP 至少支援：

```text
get_run(run_id)
get_events(run_id)
get_causal_children(event_id)
get_causal_parents(event_id)
get_attempts(run_id)
get_human_checkpoints(run_id)
get_budget_usage(run_id)
get_artifact_lineage(artifact_id)
get_validation_state(run_id)
get_commit_state(run_id)
replay_run(run_id)
```

---

# 54. Interaction Work

若 event weight：

$$
w(e),
$$

則：

$$
W_I
=
\sum_e w(e).
$$

v0.1 不規定唯一 weight。

可選：

```text
unit event count
machine_runtime_ms
normalized compute
task-relative value weight
```

Measurement contract 必須記錄。

---

# 55. Interaction Depth

以 causal DAG：

$$
G_I=(V,E).
$$

定義：

$$
D_I
=
\max_{\pi}
\sum_{e\in\pi}w(e).
$$

MVP 可以先以：

```text
unit weight
```

計算 longest path。

---

