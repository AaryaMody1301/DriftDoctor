# Improvement Changelog

This is the evidence-linked project evolution log. Failed, removed, incomplete, superseded, and corrected experiments are preserved rather than rewritten after the fact.

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
| Iteration 10 — specialized repair skills | Move recurring, well-specified dbt repairs into explicit skills derived from visible project structure and `BUSINESS_CONTEXT.md`; keep the LLM only as fallback. | First Phase 8 run reached 12/12 on the frozen benchmark. | **Promising but not final.** A mutation/generalization test subsequently exposed an overly fuzzy derived-field alias, so the first 12/12 provenance was not treated as final. |
| Iteration 11 — generalization correction | Keep the failing mutation test and fix the router generically so explicitly documented derivations outrank fuzzy source aliases. | `tests/test_repair_skills.py`; corrected repair-code SHA `0c6cf9b42863db4f45a94add11509988bcaa7815`; all 9 anti-leakage/generalization tests passed. | **Keep.** Re-run the full frozen benchmark on the corrected code before freezing evidence. |
| Iteration 12 — corrected final measurement | Run both the skills-only ablation and the actual hybrid product entry point on the same corrected code. | Workflow `33257030328`, `evidence/phase8/`: skills-only **12/12**, 7.066s/case; hybrid **12/12**, **12/12 root-cause accuracy**, **6.9895s/case**, **0 model calls**, **0 fallback cases**, zero infra errors. | **Keep hybrid as the final architecture.** The model remains available for ambiguity, but every declared benchmark case was solved before fallback. |
| Iteration 13 — submission hardening | Freeze both corrected artifacts/digests, make expensive measurement workflows manual-only, route the judge CLI through v4, and enforce anti-leakage, evidence, action-pin, claim-scope, and safety gates in CI. | `evidence/phase8/manifest.json`, `scripts/run_incident.py`, `scripts/submission_preflight.py`, `docs/PHASE_8.md`. | **Keep.** Report 12/12 only as a result on the declared benchmark; do not claim arbitrary open-ended repair generalization. |
| Final | Freeze the hybrid product: high-confidence skills → executable checks → bounded local-model fallback for unresolved cases → human approval. | `README.md`, `REPRODUCE.md`, `docs/VIDEO_PLAN.md`, `evidence/phase8/`. | **Submission candidate.** Repository/code/evidence are complete once final `main` CI is green; video recording/upload and portal submission remain manual. |

## Final controlled comparison

| System | Context | Complete | VRR | Root-cause accuracy | Mean model calls/turns | Mean elapsed |
|---|---|---:|---:|---:|---:|---:|
| matched-context simple-agent baseline | v0.2 | 12/12 | **0/12 (0%)** | 0/12 (0%) | 11.75 | 39.15s |
| Phase 5 staged LLM workflow | v0.2 | 12/12 | **1/12 (8.33%)** | 3/12 (25%) | 2.58 | 185.21s |
| semantic-review ablation | v0.2 | 7/12 scored | **unscored** | unscored | partial | partial |
| Phase 8 skills-only ablation | v0.2 | 12/12 | **12/12 (100%)** | **12/12 (100%)** | **0.0** | **7.066s** |
| **Phase 8 hybrid entry point** | **v0.2** | **12/12** | **12/12 (100%)** | **12/12 (100%)** | **0.0** | **6.9895s** |

The primary matched-context improvement is therefore **0/12 → 12/12 VRR (+100 percentage points)**. The prior staged system is retained as evidence that structure/retries alone were insufficient.

## Resource interpretation

The final system uses **fewer** model resources on the primary benchmark: zero calls. This is intentional. The intervention is a specialized skill/tool layer for high-confidence repair classes. The configured Qwen2.5-Coder 1.5B model remains only as fallback for cases that do not match those skills.

All 12 frozen benchmark cases matched deterministic skills, so fallback was not exercised by the final hybrid run. This is evidence about the declared contract-drift benchmark and the value of specialized tools—not evidence of arbitrary open-ended dbt repair capability.

## What the experiments taught us

1. **Evaluation validity comes before optimization.** Required business contracts must be visible to the system being judged.
2. **Verification without a discriminating repair mechanism is not enough.** Phase 4 added retries but produced no VRR gain.
3. **Small models can diagnose better than they patch.** Phase 5 frequently recognized the failure yet generated an invalid or unchanged edit.
4. **Specialized tools should absorb deterministic work.** Recurring contract repairs are faster and more reliable as inspectable transformations than as repeated free-form generation.
5. **A fallback is different from a default.** The model is retained for ambiguity, but it should not be invoked when visible contracts already determine the safe transformation.
6. **A perfect benchmark score still needs adversarial checks.** The mutation test that failed after the first 12/12 run prevented us from freezing a brittle implementation.
7. **Partial runs are not scores.** The semantic-review experiment remains explicitly unscored.
8. **The best agent improvement was knowing when not to call the model.** Agent engineering is routing, tools, verification, and stopping rules—not maximizing agent/model count.
