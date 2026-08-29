# Improvement Changelog

This file is the evidence-linked evolution log required for the hackathon submission. Results are preserved even when an experiment fails.

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline definition | Freeze one general-purpose coding-agent prompt before implementing DriftDoctor so the comparison cannot be retrofitted to favor the final workflow. | `baseline/PROMPT.md`; Phase 3 artifact. Baseline v0.1 VRR: **0/12 (0.0%)**; mean time **48.0s/case**. | Preserve as the original baseline. The 1.5B model frequently emitted invalid actions or weak edits. |
| Iteration 1 - evaluation-first foundation | Define the primary metric, 12 incidents, deterministic oracle requirements, fairness rules, and one challenging multi-fault case before agent implementation. | `docs/EVALUATION.md`, `benchmark/cases.json`, `scripts/validate_benchmark.py`. | Keep. It prevents moving the goalposts and makes later changes measurable. |
| Iteration 2 - executable benchmark | Materialize each incident as a synthetic dbt + DuckDB workspace and grade repairs with an external deterministic evaluator. | `benchmark/fixture_factory.py`, `benchmark/oracles.py`, `benchmark/reference_repairs.py`, smoke CI. | Keep. The evaluator catches semantic failures even when `dbt build` is green. |
| Iteration 3 - DriftDoctor v0.1 | Add deterministic evidence collection, dbt artifacts, an evidence-first repair loop, semantic review, and bounded retries using the same Qwen2.5-Coder 1.5B model. | `docs/PHASE_4_RESULT.md`; Phase 4 artifact. VRR: **0/12 (0.0%)**; mean time **211.7s/case**; **14 verifier retries**. | **Do not present as an improvement.** It reduced malformed protocol turns but did not improve VRR and was ~4.4x slower. Extra orchestration without a discriminating new signal can make an agent slower without making it better. |
| Iteration 4 - evaluation-context audit | Inspect failed trajectories and compare visible workspace information with hidden oracle expectations. Several cases referred to a "documented" rule that was not actually present in the agent workspace. | `benchmark/public_context.py`; DD-010 timezone rule and DD-011 refund-sign rule are now explicit visible business context while oracle code remains hidden. | Version the visible context as v0.2 and rerun all compared systems. Do not compare v0.1 and v0.2 results as though the benchmark context were unchanged. |
| Iteration 5 - controlled Phase 5 experiments | Test three systems on identical v0.2 visible context: simple context-aware baseline; schema-constrained staged DriftDoctor without semantic review; same staged workflow with semantic review. | `.github/workflows/phase5.yml`, `scripts/run_phase5.py`, `driftdoctor/v2.py`. | Running. Keep only interventions supported by measured evidence. |
| Final | Not started. | Not measured. | Pending Phase 5 selection and submission hardening. |

## Phase 5 experiment hypotheses

1. **Visible contract context** should improve solvability when the incident references a documented business rule.
2. **JSON-schema constrained outputs** should eliminate malformed action/patch responses. Ollama supports a JSON schema in the chat `format` field.
3. **Staged diagnose -> patch -> deterministic build** should use model calls more efficiently than an open-ended action loop.
4. **Semantic review** is only worth keeping if it improves VRR enough to justify its additional latency/model calls.
5. **More orchestration is not assumed to be better.** Phase 4 is retained as the explicit negative result.

The final submission must distinguish changes to evaluation context from changes to agent architecture and must report both successful and failed experiments.
