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
