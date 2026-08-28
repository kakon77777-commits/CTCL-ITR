# Interaction-Time Runtime & Agent Temporal Ledger v0.1

## 互動時間 Runtime 與 Agent 時間帳本工程白皮書

**文件編號**：EML-ITR-ATL-2026-v0.1  
**作者**：Neo.K（許筌崴）with Aletheia（GPT-5.6 Sol）  
**機構**：EveMissLab／一言諾科技有限公司  
**日期**：2026-08-20  
**狀態**：Engineering Whitepaper / MVP Contract  
**直接前置**：AI 互動時間與智能時間經濟學系列 01–08  
**相容前置**：ISF Execution Runtime v0.3、Temporal Loop Runtime v0.1、WDC/TCD、AICL Authority Layer

---

## 摘要

「AI 互動時間與智能時間經濟學」主系列建立了八個逐層對象：Interaction Time、Intent Cycle、Execution Trajectory、Interaction Topology、Compute Allocation、Delegated Time、Run Quality、World Time / Historical Sedimentation。若這些概念只存在於論文中，工程系統仍然會退回最常見的扁平紀錄方式：`prompt → response`、`started_at → ended_at`、`tokens → cost`、`success → true/false`。這不足以回答 Agent runtime 中真正重要的問題，例如：一個可見回合內究竟執行幾輪 control loop？哪個 action 依賴哪個 observation？某次 retry 是否真的重做相同工作？哪個 checkpoint 可恢復？某個結果是否已驗證？某個 action 有沒有 authority？一個 sandbox candidate 是否真的 commit 到 parent world？人類實際花了多少不可替代治理時間？

本文提出 **Interaction-Time Runtime（ITR）** 與 **Agent Temporal Ledger（ATL）** 的第一版工程契約。ITR 不是新的 executor，也不取代 workflow engine、OpenTelemetry、ISF 或 Temporal Loop Runtime；它是一個上位的、runtime-neutral temporal-accounting / causal-audit layer。其最小鏈條為：

$$
\boxed{
Intent
\rightarrow
Plan
\rightarrow
Run
\rightarrow
Attempt
\rightarrow
Loop
\rightarrow
Event
\rightarrow
Validation
\rightarrow
Completion
\rightarrow
Commit.
}
$$

ATL 則把每一個可觀測狀態轉換寫成 append-only ledger event，並同時保存：

```text
identity
causality
logical time
wall-clock time
machine time
human governance time
budget delta
quality delta
authority
artifact lineage
checkpoint
recovery
world commit
provenance
```

本文第一版採 JSON Schema Draft 2020-12 描述資料契約；event envelope 設計為 CloudEvents-compatible；跨服務 trace 可以映射 W3C Trace Context 與 OpenTelemetry。OpenTelemetry 目前已提供 GenAI `invoke_agent`、`plan`、`execute_tool` 等 operation conventions，但 ITR/ATL 另外保留 explicit `causal_parent_ids[]`，因為 Agent graph 可能存在多父 Join、soft dependency、branch merge 與 world-commit edge，單一 span-parent tree 不足以完整表達互動拓撲。

ITR/ATL 的核心不變量是：

$$
\boxed{
\text{Intent}
\neq
\text{Plan}
\neq
\text{Execution History}
\neq
\text{Artifact}
\neq
\text{World Commit}.
}
$$

以及：

$$
\boxed{
\text{Execution Trace}
\neq
\text{Private Chain-of-Thought}.
}
$$

系統只需保存可審計的控制流、工具、狀態、輸入輸出引用、validator、budget、authority 與 commit receipt；不要求保存或公開模型私有推理文字。

本白皮書同時附帶可直接實作的 JSON Schemas、SQLite DDL、JSONL 範例事件流與 Python validator，作為 v0.1 MVP 契約。

---

# 1. 工程目標

ITR/ATL v0.1 解決五個問題：

1. **一輪不是一步**：可見 turn 與內部 action / loop 分離。
2. **時間不是單一欄位**：world time、wall-clock、machine runtime、human governance time、logical index 分離。
3. **狀態不是 history**：current state 可由 append-only events 重建。
4. **candidate 不是 commit**：內部成功與真實世界作用分離。
5. **output 不是 quality**：completion、verification、result、governance、world integrity 分離。

---

# 2. 非目標

v0.1 不做：

- 新 LLM framework；
- 新 workflow language；
- 新 distributed trace 標準；
- 新 chain-of-thought 儲存格式；
- exactly-once external side-effect 保證；
- 通用 Agent capability leaderboard；
- 自動判定 AI 主體性；
- 取代 OpenTelemetry、CloudEvents、W3C Trace Context；
- 取代 ISF Execution Runtime。

ITR/ATL 是：

$$
\boxed{
\text{runtime-neutral temporal / causal / governance ledger}.
}
$$

---

# 3. 與既有 Runtime 的分工

## 3.1 ISF v0.3

ISF v0.3 已有：

$$
Runtime_{ISF}
=
(E,A,S,C,R,K,B,I),
$$

其中：

- Event Store；
- Artifact Store；
- Scheduler；
- Checkpoint / Replay；
- Retry / Recovery；
- Cache；
- Budget；
- Isolation。

ITR/ATL 不重做它。

ITR 將 ISF event 投影為較通用：

$$
Event_{ITR}.
$$

例如：

```text
task.started
→ event_type = action.started

task.succeeded
→ event_type = action.completed

validation.completed
→ event_type = validation.completed

budget.exceeded
→ event_type = budget.exceeded
```

---

## 3.2 Temporal Loop Runtime

Temporal Loop Runtime 已定義：

```text
persist
suspend
wake
reload
validate
resume
timeout/degrade
```

ITR 對應事件：

```text
loop.suspended
loop.wake_registered
loop.woken
loop.resumed
loop.timeout
loop.degraded
```

ITR 的工作是讓這些 loop event 能與：

- intent；
- attempt；
- budget；
- human decision；
- quality；
- world commit；

落在同一 ledger。

---

# 4. ITR 核心物件模型

第一版核心物件：

```text
Intent
Plan
Run
Attempt
Loop
TemporalEvent
ArtifactRef
Checkpoint
ValidationRecord
AuthorityRef
CommitReceipt
RunSummary
```

包含關係：

$$
Intent
\supset
Run
\supset
Attempt
\supset
Loop
\supset
Event.
$$

但 causal graph 不必與 containment tree 相同。

---

# 5. Intent Object

最小 Intent：

```json
{
  "intent_id": "intent:demo-001",
  "version": 1,
  "goal": "Generate and validate a release artifact",
  "hard_constraints": [
    "do_not_publish_without_approval"
  ],
  "soft_preferences": [
    "minimize_human_interruptions"
  ],
  "forbidden_states": [
    "unapproved_external_publish"
  ],
  "success_criteria": [
    "artifact_created",
    "tests_passed",
    "approval_received",
    "commit_receipt_present"
  ],
  "authority_scope": "internal_prepare_only",
  "risk_class": "medium"
}
```

ITR 不假設 Intent 等於原始 prompt。

---

# 6. Run

一個 Run 是某個 Intent Version 在固定 execution contract 下的一次不可覆寫執行實例。

```text
run_id
intent_id
intent_version
plan_id
plan_version
runtime_id
executor_version
created_at
status
```

核心規則：

$$
\boxed{
Run_{failed}
\rightarrow
Run_{new}
}
$$

而不是：

$$
Run_{failed}
\rightarrow
\text{rewrite history}.
$$

---

# 7. Attempt

Attempt 表示 Run 中某一局部工作或策略的嘗試。

```text
attempt_id
parent_attempt_id?
retry_of?
branch_id?
strategy_ref?
```

因此可區分：

```text
first try success
retry success
replan success
recovery success
```

---

# 8. Loop

Loop 是 control-flow 層，而不只是 `while`。

```text
loop_id
loop_type
phase
wake_rule
resume_policy
timeout_policy
checkpoint_ref
```

v0.1 建議 loop type：

```text
deliberation
tool_cycle
human_decision
event_wait
inter_agent_coordination
retry
recovery
validation
long_horizon
```

---

# 9. TemporalEvent

**TemporalEvent 是 ATL 的原子帳本單位。**

最小形式：

$$
e
=
(
id,
type,
actor,
parents,
time,
cost,
state,
status
).
$$

v0.1 JSON object 使用：

```text
specversion
event_id
event_type
source
subject
occurred_at
recorded_at
run_id
attempt_id
loop_id
interaction_round
action_index
causal_parent_ids[]
actor
data
```

其中 `specversion` 是 ITR event schema version，不是假裝成 CloudEvents spec version；如需 CloudEvents delivery，使用 adapter 包裝。

---

# 10. Event Identity

`event_id` MUST 在 ledger scope 唯一。

建議格式：

```text
evt_<uuid>
```

或 content-independent sortable ID。

不可使用：

```text
task-name
timestamp-only
array-index-only
```

作唯一 identity。

---

# 11. Causal Parent

每個 event 可有：

```json
"causal_parent_ids": [
  "evt_a",
  "evt_b"
]
```

因此 Join：

$$
e_a
\prec
e_j,
\qquad
e_b
\prec
e_j
$$

可以直接表示。

ITR 刻意不只使用單一 `parent_event_id`。

---

# 12. Containment 與 Causality 分離

例如：

- Event 屬於 Loop A；
- 但依賴 Loop B 的 artifact；
- 又等待 Human checkpoint C。

因此：

$$
\boxed{
\text{Containment Tree}
\neq
\text{Causal DAG}.
}
$$

資料模型必須同時保存：

```text
run_id / loop_id
causal_parent_ids[]
```

---

# 13. Logical Time

ATL 保存：

```text
interaction_round
loop_sequence
action_index
run_sequence
```

其中：

$$
r
=
interaction\_round,
$$

$$
k
=
loop\_sequence,
$$

$$
j
=
action\_index.
$$

這些是 logical index，不是 wall-clock timestamp。

---

# 14. Wall-Clock Time

每 event 可保存：

```text
occurred_at
recorded_at
started_at?
ended_at?
```

`occurred_at` 表示 operation semantics 中的發生時間。

`recorded_at` 表示 ledger 實際寫入時間。

兩者可能不同。

---

# 15. Machine Runtime

事件可以保存：

```text
machine_runtime_ms
cpu_time_ms?
accelerator_time_ms?
queue_wait_ms?
external_wait_ms?
```

v0.1 只要求：

```text
machine_runtime_ms
```

其他為 optional extension。

---

# 16. Human Time

ATL 對 human time 第一版至少拆：

```text
human_active_ms
human_governance_ms
human_review_ms
human_wait_ms
```

原因：

$$
\boxed{
\text{Human Wall Time}
\neq
\text{Human Governance Time}.
}
$$

例如 Agent 跑 30 分鐘，人類只在最後花 40 秒決策。

---

# 17. Budget Ledger

每 event 可有：

```json
"budget": {
  "token_in": 1000,
  "token_out": 250,
  "reasoning_tokens": 120,
  "tool_calls": 1,
  "money_microunits": 0,
  "machine_runtime_ms": 700
}
```

ATL 不假設 token、money、runtime 可以直接相加。

Budget 是向量：

$$
\mathbf B
=
(
B_{token},
B_{compute},
B_{tool},
B_{parallel},
B_{runtime},
B_{money},
B_{human}
).
$$

---

# 18. Budget Delta 與 Cumulative State

Ledger event 保存 delta：

$$
\Delta B_e.
$$

Run Summary 可 fold 得到：

$$
B_t
=
B_0
-
\sum_e\Delta B_e.
$$

不應每次 event 都把 mutable aggregate 當唯一真相。

---

# 19. Artifact Reference

Artifact 不直接塞進 event。

使用：

```json
{
  "artifact_id": "sha256:...",
  "media_type": "application/json",
  "role": "validator_result",
  "uri": "artifact://sha256/..."
}
```

保持：

$$
\boxed{
\text{Event}
\neq
\text{Artifact Bytes}.
}
$$

---

# 20. Provenance

Event 可引用：

```text
input_refs[]
output_refs[]
artifact_refs[]
source_refs[]
provenance_ref
```

這讓：

$$
Intent
\rightarrow
Event
\rightarrow
Artifact
\rightarrow
Validation
\rightarrow
Commit
$$

可追蹤。

---

# 21. Authority

任何可能造成 side effect 的 event SHOULD 有：

```json
"authority": {
  "authority_ref": "auth:demo",
  "principal": "user:neo",
  "scope": ["prepare", "validate"],
  "expires_at": "2026-08-20T12:00:00+08:00",
  "requires_fresh_approval": false
}
```

核心規則：

$$
CredentialValid
\not\Rightarrow
AuthorityValid.
$$

---

# 22. Side-Effect Classification

Action event SHOULD 標記：

```text
effect_class
```

v0.1：

```text
none
read_only
sandbox_mutation
external_reversible
external_compensatable
external_irreversible
```

因此：

$$
\text{rollback semantics}
$$

不會被所有 action 混成一種。

---

# 23. Candidate / Commit 分離

`action.completed` 不代表 world commit。

必須有獨立：

```text
commit.proposed
commit.authorized
commit.executed
commit.confirmed
```

或至少：

```text
world.commit
```

事件 + `CommitReceipt`。

---

# 24. CommitReceipt

最小 commit receipt：

```text
commit_id
run_id
intent_id
authority_ref
candidate_ref
target
effect_class
executed_at
external_confirmation
state_before_ref?
state_after_ref?
validator_refs[]
provenance_ref
```

核心：

$$
\boxed{
\text{Candidate}
\neq
\text{Commit}.
}
$$

---

# 25. World Commit 狀態

v0.1：

```text
not_applicable
candidate
awaiting_authority
authorized
executed
confirmed
compensated
failed
```

不要只用：

```text
world_commit: true/false
```

因為真實世界作用具有生命週期。

---

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

# 81. Authority Resolver Contract

```text
check(principal, action, target, context)
→ allow | deny | step_up | expired
```

Authority decision MUST 產生 ledger event。

---

# 82. Commit Adapter Contract

```text
propose(candidate)
authorize(authority)
execute(execution_key)
confirm(external_state)
compensate(reason)
```

每階段都可產生 receipt。

---

# 83. OpenTelemetry Exporter Contract

ITR exporter SHOULD：

- `run` → root `invoke_agent` or application span；
- planning → `plan`；
- model calls → inference span；
- tools → `execute_tool`；
- attributes → model / token / tool metadata；
- span links → extra causal parents。

但 OpenTelemetry export 失敗不能破壞 canonical ATL ledger。

---

# 84. CloudEvents Adapter Contract

CloudEvents adapter：

```text
ITR TemporalEvent
→ CloudEvents data
```

不得把 transport ID 取代 canonical `event_id`。

---

# 85. Replay Determinism

若 executor / world effect 不重跑，只 replay ledger：

$$
Replay(H_r)
\rightarrow
StateProjection.
$$

應 deterministic。

如果同一 ledger 得出不同 projection：

$$
\boxed{
\text{Projection Bug}.
}
$$

---

# 86. Schema Evolution

所有 object MUST 有：

```text
schema_version
```

v0.x 演化規則：

- add optional field：compatible；
- rename field：breaking；
- change meaning：breaking；
- narrow enum：breaking；
- widen enum：usually compatible but consumers must ignore unknown values。

---

# 87. Unknown Field Policy

JSON Schema v0.1 對核心 object 使用：

```text
additionalProperties: false
```

以避免 typo silently accepted。

Extension 使用：

```text
extensions
```

object。

---

# 88. Extension Namespace

```json
"extensions": {
  "org.evemiss.phosphor": {},
  "org.opentelemetry": {},
  "vendor.example": {}
}
```

避免把 vendor-specific field 混入 core namespace。

---

# 89. Security

Ledger SHOULD 防：

- path traversal；
- event spoofing；
- duplicate ID；
- authority substitution；
- artifact tampering；
- replay attack；
- secret leakage；
- cross-run contamination。

---

# 90. Run Isolation

Run workspace / namespace MUST 分離。

Artifact 可以 global content-addressed reuse，但 provenance observation 必須是 run-relative。

---

# 91. Hash / Digest

核心 canonical refs 建議：

```text
sha256:<hex>
```

白皮書不規定永遠只能 SHA-256；v0.1 使用它作 reference profile。

---

# 92. Reference Acceptance Tests

v0.1 工程包應通過：

1. JSON Schemas 可被 Draft 2020-12 validator 載入；
2. sample intent valid；
3. sample run valid；
4. sample events 每行 valid；
5. event_id 唯一；
6. ledger_seq 單調；
7. causal parents 均指向已知或明確 external parent；
8. sample checkpoint valid；
9. sample commit receipt valid；
10. sample run summary valid；
11. hard forbidden state 未被觸發；
12. commit 前具有 approval；
13. commit receipt 指回 candidate；
14. validation pass 在 run success 前存在；
15. artifact refs 採合法 digest format。

---

# 93. MVP 的最小資料庫

第一版只需要：

```text
SQLite
+
JSON artifacts
+
JSON Schema
```

不需要：

- Kafka；
- graph DB；
- distributed consensus；
- vector DB。

先證明語義，再擴基礎設施。

---

# 94. v0.2 Roadmap

v0.2：

- multi-agent branch/join demo；
- critical path calculator；
- OTel exporter；
- CloudEvents adapter；
- event hash chain；
- policy engine；
- human approval queue；
- richer budget vectors；
- span links mapping。

---

# 95. v0.3 Roadmap

v0.3：

- distributed workers；
- lease / fencing；
- cross-process resume；
- external commit reconciliation；
- PHOSPHOR timeline / DAG UI；
- Agent Temporal Ledger analytics；
- autonomy horizon / governance horizon metrics。

---

# 96. v0.4 Roadmap

v0.4：

- multi-runtime federation；
- ISF / WDC / CTCL / AICL adapters；
- durable world commit receipts；
- historical sedimentation service；
- organizational / civilizational time aggregation。

---

# 97. 與八篇主系列的逐篇映射

## Paper 01 — Interaction Time

ATL：

```text
event
causality
typed time
```

## Paper 02 — Intent Cycle

ATL：

```text
intent_id
intent_version
success_criteria
authority
```

## Paper 03 — One Turn Is Not One Step

ATL：

```text
run
attempt
loop
action
observation
retry
recovery
```

## Paper 04 — Interaction Topology

ATL：

```text
causal_parent_ids[]
interaction_work
interaction_depth
```

## Paper 05 — Compute Economics

ATL：

```text
budget delta
token
compute
tool
money
human time
```

## Paper 06 — Delegated Time

ATL：

```text
human checkpoint
authority
governance time
delegation span
```

## Paper 07 — Run Quality

ATL：

```text
quality vector
completion
verification
hard gate
```

## Paper 08 — World Time

ATL：

```text
commit receipt
world confirmation
historical sedimentation handoff
```

---

# 98. 最終工程鏈

$$
\boxed{
Intent
\rightarrow
Plan
\rightarrow
Run
\rightarrow
Attempt
\rightarrow
Loop
\rightarrow
Action
\rightarrow
Observation
\rightarrow
Validation
\rightarrow
Completion
\rightarrow
Authority
\rightarrow
Commit
\rightarrow
World.
}
$$

---

# 99. 最小核心

如果所有進階功能都刪掉，ITR/ATL 仍必須保留：

```text
append-only event
causal parent
typed time
run identity
artifact reference
validation
budget
human checkpoint
authority
commit receipt
```

這十項是 v0.1 的最低不可再刪核心。

---

# 100. 結論

Interaction-Time Runtime & Agent Temporal Ledger v0.1 的目的不是讓 Agent 多記一些 log。

它要改變的是：

$$
\boxed{
\text{我們究竟把什麼叫做一次 AI 工作？}
}
$$

從：

```text
prompt
response
duration
tokens
success
```

提升為：

```text
intent
plan
run
attempt
loop
event
causality
budget
human time
validation
quality
authority
artifact
checkpoint
commit
```

因此一個 Agent 系統終於可以回答：

- 這一輪到底做了多少事？
- 哪些是必要因果深度？
- 哪些是浪費？
- 哪些是 retry？
- 哪些是 parallel branch？
- 人類何時介入？
- 人類花了多少真正治理時間？
- 哪些結果通過驗證？
- 哪個 action 有 authority？
- 哪個 candidate 真的 commit 到世界？
- 如果 crash，從哪裡恢復？
- 如果結果錯，錯誤起點在哪裡？
- 如果今天比昨天生產力高，是模型變強、額度增加、流程改善、委任增加，還是驗證品質變好？

這就是「互動時間」從理論進入 Runtime 的第一步。

$$
\boxed{
\text{Agent Time}
\rightarrow
\text{Observable Causal Ledger}
\rightarrow
\text{Governable Intelligent Work}.
}
$$

---

# 參考與互操作基線

## EveMissLab

1. 《AI 互動時間與智能時間經濟學系列》01–08，2026。
2. 《Intent-to-System Flow Execution Runtime Specification》v0.3。
3. 《Temporal Loop Runtime：時間迴圈執行器工程規格》v0.1。
4. 《WDC-08: Tri-Temporal World-Domain Computation》v0.1。
5. 《AICL-I: AI Ingestion Capability Layer》v0.2。
6. 《BRIDGE_MATRIX》。

## 外部標準／規格

7. OpenTelemetry Semantic Conventions 1.44.0，2026。
8. OpenTelemetry GenAI Semantic Conventions repository，Agent / planning / tool spans，Development status。
9. W3C Trace Context。
10. CloudEvents specification。
11. JSON Schema Draft 2020-12。

---

## 一句話版本

> **ITR/ATL 不把 AI 工作記成「一次回答」，而把它記成一條可恢復、可驗證、可治理、可追溯到世界提交的因果事件鏈。**

---

*EML-ITR-ATL-2026-v0.1*
