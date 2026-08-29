# Submission readiness checklist

This checklist maps DriftDoctor's final package to the hackathon deliverables and scoring criteria. Items that depend on the corrected Phase 5 experiment remain intentionally open until all three systems complete without infrastructure errors.

## Required deliverables

- [x] Complete source code for benchmark, baseline, agent workflow, evaluation, and experiment harness.
- [x] Improvement Changelog includes the evaluation-first foundation and executable benchmark.
- [x] Preserve Phase 4 as a measured failed experiment rather than rewriting history.
- [x] Clean-environment reproduction guide (`REPRODUCE.md`).
- [x] Case-level observable trajectories and tool/model outputs are stored in evaluation evidence.
- [ ] Freeze complete Phase 5 results for all comparison systems.
- [ ] Select final workflow using the predeclared rule: VRR first, then model calls/latency.
- [ ] Update Improvement Changelog with final Phase 5 numbers and removal/retention decision for semantic review.
- [ ] Produce final comparison table using only complete, matched-context runs.
- [ ] Add a concise final failure-mode + hot-take section to README.
- [ ] Record final commit SHA and clean reproduction runtime.
- [ ] Record a <=5 minute solution video.
- [ ] Include one realistic end-to-end run, baseline/final comparison, changelog, biggest contribution, and one removed/failed experiment in the video.

## Rubric audit

### Problem & User Value — 15

- [x] Primary user is analytics/data engineers maintaining dbt projects.
- [x] Bottleneck is evidence-heavy incident diagnosis plus safe repair verification.
- [x] Product boundary is concrete: schema, contract, dependency, data-quality, and semantic drift in dbt pipelines.
- [ ] README final pass states the before/after user workflow in under 30 seconds of reading.

### Agent Solution & Engineering — 30

- [x] Deterministic evidence gathering from dbt execution/artifacts and project files.
- [x] Structured diagnosis and patch generation.
- [x] Guarded writes restricted to intended project code.
- [x] Deterministic build feedback.
- [x] Semantic-review ablation exists rather than assuming more agents/components help.
- [x] Hidden oracle is not exposed to the repair workflow.
- [ ] Freeze only the measured winning workflow.

### End-to-End Quality — 20

- [x] Starts from a broken local dbt project and ends in a concrete patch plus executable verification.
- [x] Silent semantic failures can be caught by the external evaluator even when `dbt build` is green.
- [x] Synthetic workspace prevents production side effects.
- [ ] Add judge-facing CLI/report polish for the selected final workflow.
- [ ] Demonstrate one approval-ready repair report in the video.

### Measured Improvement — 15

- [x] One primary metric: Verified Resolution Rate (VRR).
- [x] 12 reproducible cases including one multi-fault challenge case.
- [x] Original baseline and Phase 4 measurements are preserved.
- [x] Context-v0.2 baseline exists for fair Phase 5 comparison.
- [ ] Corrected Phase 5 matrix completes 12/12 for every selected comparison arm.
- [ ] Headline improvement claim is generated from complete matched-context evidence only.

### Reproducibility — 15

- [x] Pinned Python/dbt/DuckDB versions.
- [x] Synthetic local data and DuckDB; no warehouse credentials.
- [x] Reference repairs prove oracle solvability.
- [x] `REPRODUCE.md` contains exact install/evaluation commands.
- [x] CI validates benchmark and stores evidence artifacts.
- [ ] Final clean-run commit and artifact digest recorded.

### Hot Take / Insights — 5

Evidence-backed candidates; do not freeze wording until Phase 5 completes:

1. A verifier is not automatically useful: Phase 4 added 14 verifier-triggered retries but improved VRR by zero.
2. Better protocol compliance is not the same as better task success: invalid action turns fell substantially while verified repair rate stayed flat.
3. An evaluation can be deterministic and still be invalid if required business context is hidden from the agent.
4. For repair agents, deterministic executable verification plus explicit business contracts may matter more than adding agent count.

## Evidence-integrity rules

- Never publish a VRR from a partial run.
- Never count an infrastructure timeout as a task failure without labeling it.
- Never compare v0.1 and v0.2 context runs as a controlled agent-only comparison.
- Never expose reference repairs or hidden oracle logic to the repair agent.
- Never rewrite or delete a failed experiment solely because it hurts the final narrative.
- Every final quantitative claim must point to an exact result artifact or reproducible command.
