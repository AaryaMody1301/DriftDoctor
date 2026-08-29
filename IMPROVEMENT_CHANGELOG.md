# Improvement Changelog

This file is the evidence-linked evolution log required for the hackathon submission. Results are preserved even when an experiment fails.

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline definition | Freeze one general-purpose coding-agent prompt before implementing DriftDoctor so the comparison cannot be retrofitted to favor the final workflow. | `baseline/PROMPT.md`; Phase 3 artifact. Baseline v0.1 VRR: **0/12 (0.0%)**; mean time **48.0s/case**. | Preserve as the original baseline. The 1.5B model frequently emitted invalid actions or weak edits. |
| Iteration 1 - evaluation-first foundation | Define the primary metric, 12 incidents, deterministic oracle requirements, fairness rules, and one challenging multi-fault case before agent implementation. | `docs/EVALUATION.md`, `benchmark/cases.json`, `scripts/validate_benchmark.py`. | **Keep.** It prevents moving the goalposts and makes later changes measurable. |
| Iteration 2 - executable benchmark | Materialize each incident as a synthetic dbt + DuckDB workspace and grade repairs with an external deterministic evaluator. | `benchmark/fixture_factory.py`, `benchmark/oracles.py`, `benchmark/reference_repairs.py`, smoke CI. | **Keep.** The evaluator catches semantic failures even when `dbt build` is green. |
| Iteration 3 - DriftDoctor v0.1 | Add deterministic evidence collection, dbt artifacts, an evidence-first repair loop, semantic review, and bounded retries using the same Qwen2.5-Coder 1.5B model. | `docs/PHASE_4_RESULT.md`; Phase 4 artifact. VRR: **0/12 (0.0%)**; mean time **211.7s/case**; **14 verifier retries**. | **Reject as an improvement.** It reduced malformed protocol turns but did not improve VRR and was ~4.4x slower. Extra orchestration without a discriminating new signal can make an agent slower without making it better. |
| Iteration 4 - evaluation-context audit | Inspect failed trajectories and compare visible workspace information with hidden oracle expectations. Several cases referred to a "documented" rule that was not actually present in the agent workspace. | `benchmark/public_context.py`; DD-010 timezone rule and DD-011 refund-sign rule are explicit visible business context while oracle code remains hidden. | Version the visible context as v0.2 and rerun all compared systems. Do not compare v0.1 and v0.2 results as though the benchmark context were unchanged. |
| Iteration 5 - context-v0.2 baseline | Re-run a simple coding-agent baseline with the now-visible business contract so Phase 5 comparisons use matched context. | `evidence/phase5/context-baseline/`: **0/12 VRR**, **0/12 root-cause accuracy**, **39.15s mean elapsed**, **11.75 mean model calls**, zero infrastructure errors. Source run `33236007203`. | **Keep as the matched-context baseline.** Visible context alone did not solve these incidents for this model. |
| Iteration 6 - staged DriftDoctor without semantic review | Test schema-constrained diagnosis -> patch -> deterministic build feedback without the extra reviewer. | `evidence/phase5/driftdoctor-no-review/`: **1/12 VRR (8.33%)**, **3/12 root-cause accuracy (25%)**, **185.21s mean elapsed**, **2.58 mean model calls**, zero infrastructure errors. DD-004 passed every oracle check. Source run `33236007203`. | **Keep as the final measured workflow.** It is the first matched-context system to produce a verified repair and improves VRR by **+8.33 percentage points** over the matched baseline. The absolute 1/12 result remains modest. |
| Iteration 7 - semantic-review ablation | Add an adversarial semantic reviewer plus one targeted retry to test whether another model stage improves verified outcomes. | The first corrected review attempt was infrastructure-incomplete. The final three-shard recovery is preserved under `evidence/phase5/driftdoctor-review-incomplete/`: **7/12 scored**, `complete=false`, `verified_resolution_rate=null`; DD-002/004/005/007 timed out and DD-008 has no case record. | **Remove from the final workflow.** Do not fabricate a VRR from partial evidence. Operationally, the extra inference stage increased latency/transport exposure and failed to produce a complete comparable experiment before submission. |
| Iteration 8 - CI/reproducibility hardening | Replace repeated 12-runner model setup with 3 warm-model shards; cancel obsolete runs; make expensive model workflows manual-only; consolidate automatic main verification; preserve artifacts in-repo. | `.github/workflows/`, `evidence/phase5/manifest.json`, checked-in raw records and artifact SHA-256 digests. | **Keep.** Evaluation infrastructure should not compete with the experiment for runner capacity, and submission evidence should not depend on retention-limited artifacts. |
| Final | Freeze `driftdoctor-no-review`; add the disposable judge CLI, clean reproduction guide, durable evidence, preflight/benchmark CI, rubric checklist, and video plan. | `scripts/run_incident.py`, `REPRODUCE.md`, `evidence/phase5/`, `docs/SUBMISSION_CHECKLIST.md`, `.github/workflows/submission.yml`. | **Submission candidate complete.** Remaining manual work is recording/uploading the <=5 minute video and entering the project on the hackathon portal. |

## Final controlled comparison

| System | Context | Complete | VRR | Root-cause accuracy | Mean model calls | Mean elapsed |
|---|---|---:|---:|---:|---:|---:|
| context baseline | v0.2 | 12/12 | **0/12 (0.00%)** | 0/12 | 11.75 | 39.15s |
| **DriftDoctor staged / no review** | v0.2 | 12/12 | **1/12 (8.33%)** | 3/12 | 2.58 | 185.21s |
| semantic-review ablation | v0.2 | 7/12 scored | **unscored** | unscored | partial | partial |

The primary result is therefore **+1 verified incident / +8.33 percentage points VRR** under matched visible context. This is the only architecture-improvement claim made from Phase 5.

## What the experiments taught us

1. **Visible contract context matters for evaluation validity.** A deterministic oracle can still define an unfair task if required business rules are hidden from the agent.
2. **Structured outputs and staging improved execution efficiency, but not enough repair quality.** The final workflow used far fewer model calls than the context baseline yet still solved only one case.
3. **A verifier/reviewer is not automatically useful.** Phase 4's verifier loop produced zero VRR gain, and the later semantic-review ablation was operationally too expensive/unreliable to complete on the chosen free CPU setup.
4. **Partial infrastructure-failed runs are evidence about engineering, not task scores.** They remain checked in with `verified_resolution_rate=null`.
5. **More orchestration is not assumed to be better.** Every retained component must earn its place through complete measured evidence.
