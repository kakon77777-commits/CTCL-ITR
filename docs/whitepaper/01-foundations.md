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
