# Improvement Changelog

This is the evidence-linked project evolution log. Failed, removed, incomplete, and superseded experiments are preserved rather than rewritten after the fact.

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline definition | Freeze one general-purpose coding-agent prompt before implementing DriftDoctor so the comparison cannot be retrofitted to favor the final workflow. | `baseline/PROMPT.md`; historical v0.1 baseline **0/12 VRR**, ~48.0s/case. | Preserve. The small model frequently emitted invalid actions or weak edits. |
| Iteration 1 — evaluation-first foundation | Freeze one primary metric, 12 incidents, deterministic oracle checks, fairness rules, and one multi-fault challenge case before optimizing the workflow. | `docs/EVALUATION.md`, `benchmark/cases.json`, `scripts/validate_benchmark.py`. | **Keep.** Prevent moving the goalposts. |
| Iteration 2 — executable benchmark | Materialize each incident as a synthetic dbt + DuckDB project and grade it with an evaluator outside the repair workspace. | `benchmark/fixture_factory.py`, `benchmark/oracles.py`, `benchmark/reference_repairs.py`. | **Keep.** A green build is not sufficient for silent semantic regressions. |
| Iteration 3 — DriftDoctor v0.1 | Add evidence collection, dbt artifacts, semantic review, and bounded retries around the same Qwen2.5-Coder 1.5B model. | `docs/PHASE_4_RESULT.md`: **0/12 VRR**, ~211.7s/case, 14 verifier retries. | **Reject as an improvement.** More orchestration made the run slower without improving verified outcomes. |
| Iteration 4 — evaluation-context audit | Check whether hidden oracle expectations were actually available to an honest repair agent. Some cases referenced a “documented” rule that was absent from the workspace. | `benchmark/public_context.py`; v0.2 adds visible business rules while keeping oracle implementation hidden. | Version the visible context and rerun both sides. Never compare v0.1 and v0.2 as if inputs were identical. |
| Iteration 5 — context-v0.2 baseline | Re-run the simple coding-agent baseline with legitimate visible business context. | `evidence/phase5/context-baseline/`: **0/12 VRR**, **0/12 root-cause accuracy**, 39.15s/case, 11.75 mean turns. | **Keep as the matched-context baseline.** Context alone did not solve the tasks for this model. |
| Iteration 6 — staged LLM workflow | Use schema-constrained diagnosis/patch plus deterministic build feedback, without the extra semantic reviewer. | `evidence/phase5/driftdoctor-no-review/`: **1/12 VRR (8.33%)**, **3/12 root-cause accuracy**, 185.21s/case, 2.58 model calls. | **Keep as an intermediate improvement.** It produced the first matched-context verified repair, but 1/12 remained too weak. |
| Iteration 7 — semantic-review ablation | Add an adversarial model reviewer and targeted retry to test whether another inference stage improves verified outcomes. | `evidence/phase5/driftdoctor-review-incomplete/`: 7/12 scored, `complete=false`, `verified_resolution_rate=null`. | **Remove.** It increased latency/transport exposure and never produced a complete comparable result. |
| Iteration 8 — failure analysis | Inspect Phase 5 trajectories rather than adding more agents. DD-001 understood the missing field but wrote the same broken source name back; DD-003 selected an invalid narrow decimal cast; DD-005 invented a second model instead of repairing grain. | `evidence/phase5/driftdoctor-no-review/DD-001.json`, `DD-003.json`, `DD-005.json`. | Repair generation—not evidence collection—was the dominant bottleneck. |
| Iteration 9 — contract-guided LLM prototype | Add a stronger repair taxonomy/playbook and bounded build-driven retries while keeping the same 1.5B model. | `driftdoctor/v3.py`; Phase 7 PR/run history. | **Superseded before promotion.** Long local inference remained expensive, and the known high-confidence failure classes could be represented more directly as tools. |
| Iteration 10 — specialized repair skills | Move recurring, well-specified dbt repairs into explicit skills derived from visible project structure and `BUSINESS_CONTEXT.md`; keep the LLM only as fallback. | `driftdoctor/repair_skills.py`, `driftdoctor/v4.py`, `evidence/phase8/`. Frozen run `33256430999`: **12/12 VRR (100%)**, **12/12 root-cause accuracy**, **7.88s/case**, **0 model calls**, zero infra errors. | **Keep as the final architecture.** The best intervention was routing deterministic work away from a weak general model. |
| Iteration 11 — anti-overfitting/submission hardening | Add explicit anti-leakage checks, mutation-style skill probes, durable Phase 8 trajectories/provenance, and route the judge CLI through the hybrid skill-first product. | `tests/test_repair_skills.py`, `evidence/phase8/manifest.json`, `scripts/run_incident.py`, `scripts/submission_preflight.py`. | **Keep.** Report 12/12 only as a result on the declared benchmark; do not claim arbitrary open-ended repair generalization. |
| Final | Freeze the hybrid product: high-confidence skills → executable checks → bounded local-model fallback for unresolved cases → human approval. | `README.md`, `REPRODUCE.md`, `docs/PHASE_8.md`, `docs/VIDEO_PLAN.md`, `evidence/phase8/`. | **Submission candidate.** Repository/code/evidence are complete once final CI is green; video recording/upload and portal submission remain manual. |

## Final controlled comparison

| System | Context | Complete | VRR | Root-cause accuracy | Mean model calls/turns | Mean elapsed |
|---|---|---:|---:|---:|---:|---:|
| matched-context simple-agent baseline | v0.2 | 12/12 | **0/12 (0%)** | 0/12 (0%) | 11.75 | 39.15s |
| Phase 5 staged LLM workflow | v0.2 | 12/12 | **1/12 (8.33%)** | 3/12 (25%) | 2.58 | 185.21s |
| semantic-review ablation | v0.2 | 7/12 scored | **unscored** | unscored | partial | partial |
| **Phase 8 specialized-skill path** | **v0.2** | **12/12** | **12/12 (100%)** | **12/12 (100%)** | **0.0** | **7.88s** |

The primary matched-context improvement is therefore **0/12 → 12/12 VRR (+100 percentage points)**. The prior staged system is retained as evidence that structure/retries alone were insufficient.

## Resource interpretation

The final system does not get “free extra model intelligence.” It uses **fewer** model resources on the primary benchmark: zero calls. This is intentional. The intervention is a specialized skill/tool layer for high-confidence repair classes. The configured Qwen2.5-Coder 1.5B model remains only as fallback for cases that do not match those skills.

All 12 frozen benchmark cases matched a deterministic skill, so the fallback was not exercised in the final primary run. This should be read as evidence about the declared contract-drift benchmark and the value of specialized tools—not as evidence of arbitrary open-ended dbt repair capability.

## What the experiments taught us

1. **Evaluation validity comes before optimization.** Required business contracts must be visible to the system being judged.
2. **Verification without a discriminating repair mechanism is not enough.** Phase 4 added retries but produced no VRR gain.
3. **Small models can diagnose better than they patch.** Phase 5 frequently recognized the failure yet generated an invalid or unchanged edit.
4. **Specialized tools should absorb deterministic work.** Recurring contract repairs are faster and more reliable as inspectable transformations than as repeated free-form generation.
5. **A fallback is different from a default.** The model is retained for ambiguity, but it should not be invoked when visible contracts already determine the safe transformation.
6. **Partial runs are not scores.** The semantic-review experiment remains explicitly unscored.
7. **The best agent improvement was knowing when not to call the model.** Agent engineering is routing, tools, verification, and stopping rules—not maximizing agent/model count.
