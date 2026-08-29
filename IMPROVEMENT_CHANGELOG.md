# Improvement Changelog

This is the evidence-linked evolution log required by the hackathon rulebook. Failed, removed, incomplete, superseded, and corrected experiments are preserved rather than rewritten after the fact.

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
| Iteration 8 — failure analysis | Inspect Phase 5 trajectories rather than adding more agents. DD-001 understood the missing field but wrote the same broken source name back; DD-003 selected an invalid narrow decimal cast; DD-005 invented or changed the wrong structure instead of restoring grain. | `evidence/phase5/driftdoctor-no-review/DD-001.json`, `DD-003.json`, `DD-005.json`. | Repair generation—not evidence collection—was the dominant bottleneck. |
| Iteration 9 — contract-guided LLM prototype | Add a stronger repair taxonomy/playbook and bounded build-driven retries while keeping the same 1.5B model. | Historical `driftdoctor/v3.py`; Phase 7 run history. | **Superseded before promotion.** Long local inference remained expensive, and known high-confidence classes could be represented more directly as tools. |
| Iteration 10 — specialized repair skills | Move recurring, well-specified dbt repairs into explicit skills derived from visible project structure and `BUSINESS_CONTEXT.md`; retain a model as fallback. | First Phase 8 run reached 12/12 on the frozen benchmark. | **Promising but not final.** A later mutation probe exposed an overly fuzzy derived-field alias, so the first perfect run was not frozen. |
| Iteration 11 — generalization correction | Keep the failing mutation test and fix the router generically so explicitly documented derivations outrank fuzzy source aliases. | `tests/test_repair_skills.py`; corrected repair-code SHA `0c6cf9b42863db4f45a94add11509988bcaa7815`; all nine anti-leakage/generalization tests passed. | **Keep.** Re-run the full frozen benchmark on corrected code before publishing evidence. |
| Iteration 12 — corrected Phase 8 measurement | Run both skills-only and the then-current hybrid entry point on the corrected code. | Workflow `33257030328`, `evidence/phase8/`: both **12/12**, 12/12 root causes, zero model calls; hybrid 6.9895s/case. | **Keep the skills and 12-case result.** The model fallback still was not exercised by any primary case. |
| Iteration 13 — agent-role audit | Review the submission against the “Agentic Workflows” requirement. The 12/12 result proved the skill layer, but not that the model-backed agent had a purposeful measured role. The open-ended historical coding fallback was also too risky and weak. | Phase 8 evidence: `fallback_cases=0`; Phase 5 showed poor open-ended patch quality. | Replace open-ended coding fallback with **selective agency**: one bounded decision for an observed ambiguity, otherwise abstain/escalate. |
| Iteration 14 — final selective-agency runtime | Capture the broken state, run skills, invoke a constrained agent only for one missing-ref ambiguity with multiple observed candidates, verify, and escalate unsupported work. | `driftdoctor/ambiguity.py`, `driftdoctor/v4.py`, 31 unit/integrity tests. | **Keep.** The agent can choose only an existing candidate or abstain; it cannot invent paths or write arbitrary code. |
| Iteration 15 — primary no-regression measurement | Rerun all 12 frozen cases through the final selective-agency entry point to ensure the safety/agency changes did not regress the published score. | Workflow `33259014887`; `evidence/phase9/primary-summary.json`: **12/12 VRR**, 12/12 roots, 0 model calls, 0 escalations, 6.6403s/case. | **Keep.** Known contract-determined work still resolves before any model call. |
| Iteration 16 — held-out bounded-agent case | Create a separate ambiguous dependency case where deterministic structure exposes two candidates but cannot safely select one. Compare skills-only against the bounded agent. | `evidence/phase9/agent-fallback-demo.json`: skills-only build return code 2 + escalation; bounded agent uses one call, selects `stg_orders_v2`, and passes all held-out checks. | **Keep as the representative agent trajectory.** Do not fold it into the 12-case primary VRR. |
| Iteration 17 — submission/repository cleanup | Audit every rulebook requirement, preserve durable evidence, add licensing/provenance, remove obsolete Action definitions, and create one judge navigation path. | `docs/RULEBOOK_COMPLIANCE.md`, `docs/AGENT_TRAJECTORIES.md`, `docs/REPOSITORY_MAP.md`, `THIRD_PARTY_NOTICES.md`, `SUBMISSION.md`. | **Keep.** Historical evidence remains, but the active product and automation paths are now explicit. |
| Final | Freeze the product as: contract skills → bounded ambiguity agent when needed → executable verification → human approval/escalation. | `README.md`, `REPRODUCE.md`, `evidence/phase8/`, `evidence/phase9/`, `scripts/run_incident.py`. | **Repository submission candidate complete.** Human-only work is recording/uploading the ≤5-minute video and entering the final passing `main` SHA in HackerEarth. |

## Primary controlled comparison

All rows use the same 12 context-v0.2 fixtures and external evaluator.

| System | Complete | VRR | Root-cause accuracy | Mean model calls/turns | Mean elapsed |
|---|---:|---:|---:|---:|---:|
| matched-context simple-agent baseline | 12/12 | **0/12 (0%)** | 0/12 | 11.75 | 39.15s |
| staged LLM workflow | 12/12 | **1/12 (8.33%)** | 3/12 | 2.58 | 185.21s |
| corrected Phase 8 skill-first run | 12/12 | **12/12 (100%)** | **12/12** | 0.0 | 6.9895s |
| **final Phase 9 selective-agency rerun** | **12/12** | **12/12 (100%)** | **12/12** | **0.0** | **6.6403s** |

The primary matched-context improvement is therefore **0/12 → 12/12 VRR (+100 percentage points)** on the declared benchmark. Every primary case is contract-determined, so agent use is correctly zero rather than artificially forced.

## Separate agent-role evaluation

This held-out case is reported separately and does not change primary VRR.

| System | Build / verification | Model calls | Escalation |
|---|---|---:|---|
| skills-only control | failed | 0 | required |
| **bounded ambiguity agent** | all held-out checks passed | **1** | not required after repair |

The agent’s allowed output was limited to two observed existing candidate model names or `abstain`.

## What the experiments taught us

1. **Evaluation validity comes before optimization.** Required business contracts must be visible to the system being judged.
2. **Verification without a discriminating repair mechanism is not enough.** Phase 4 added retries but produced no VRR gain.
3. **Small models can diagnose better than they patch.** Phase 5 frequently recognized the class and then generated an invalid or unchanged edit.
4. **Specialized tools should absorb deterministic work.** Recurring contract repairs are faster and more reliable as inspectable transformations than repeated generation.
5. **A fallback is different from a default.** Model inference should be reserved for a decision that tools cannot safely make.
6. **Agency should be constrained by the action space.** The final agent chooses among observed candidates or abstains; it does not receive arbitrary repository-write authority.
7. **A perfect benchmark score still needs adversarial checks.** A mutation test caught a real bug after the first 12/12 run; the score was re-earned on corrected code.
8. **Partial runs are not scores.** The semantic-review experiment remains explicitly unscored.
9. **Human escalation is a feature.** Unsupported ambiguity is safer as an approval request than a confident autonomous patch.
10. **The best agent improvement was knowing when not to call the model.**
