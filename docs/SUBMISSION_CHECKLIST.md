# Submission readiness checklist

This checklist maps DriftDoctor's final package to the hackathon deliverables and scoring criteria. The measured software/evidence package is frozen; only manual portal/video steps remain.

## Required deliverables

- [x] Complete source code for benchmark, baseline, final agent workflow, evaluation, and experiment harness.
- [x] Improvement Changelog includes baseline, iterations, failed experiments, results, and final decision.
- [x] Preserve Phase 4 as a measured failed experiment rather than rewriting history.
- [x] Preserve the incomplete semantic-review ablation with a null VRR rather than converting infrastructure failures into task failures.
- [x] Clean-environment reproduction guide (`REPRODUCE.md`).
- [x] Case-level observable trajectories, tool/model outputs, diffs, and oracle outcomes preserved in `evidence/phase5/` for complete comparison arms.
- [x] Judge-facing safe CLI operates on a disposable project copy and emits an approval-ready JSON report.
- [x] README includes final matched-context numbers, concise failure mode, and evidence-backed hot take.
- [x] Freeze the publishable Phase 5 results: context baseline 0/12; final no-review workflow 1/12.
- [x] Select final workflow using the predeclared evidence rule: **`driftdoctor-no-review`**.
- [x] Update Improvement Changelog with final numbers and removal decision for semantic review.
- [x] Produce final comparison table using only complete, matched-context runs.
- [x] Preserve raw Phase 5 result records in the repository and record CI artifact IDs/digests in `evidence/phase5/manifest.json`.
- [ ] Record the final merged `main` commit SHA in the hackathon submission notes after PR #10 is merged.
- [ ] Record/upload a <=5 minute solution video.
- [ ] Submit the final repository/video on the hackathon portal.

## Rubric audit

### Problem & User Value — 15

- [x] Primary user is analytics/data engineers maintaining dbt projects.
- [x] Bottleneck is evidence-heavy incident diagnosis plus safe repair verification.
- [x] Product boundary is concrete: schema, contract, dependency, data-quality, and semantic drift in dbt pipelines.
- [x] README states the before/after user workflow and provides a one-command local incident path.

### Agent Solution & Engineering — 30

- [x] Deterministic evidence gathering from dbt execution/artifacts and project files.
- [x] Structured diagnosis and patch generation.
- [x] Guarded writes restricted to intended project code.
- [x] Deterministic build feedback creates a new signal before retry.
- [x] Semantic-review ablation was measured instead of assuming more agent stages help.
- [x] Hidden oracle is not exposed to the repair workflow.
- [x] Final system freezes only components supported by complete publishable evidence.

### End-to-End Quality — 20

- [x] Starts from a broken local dbt project and ends in a concrete patch plus executable verification/report.
- [x] Silent semantic failures can be caught by the external evaluator even when `dbt build` is green.
- [x] Synthetic workspace prevents production side effects.
- [x] Judge-facing CLI/report path uses a disposable copy, captures diff/trajectory/build evidence, and requires human approval.
- [ ] Demonstrate the DD-004 approval-ready repair/evidence path in the video.

### Measured Improvement — 15

- [x] One primary metric: Verified Resolution Rate (VRR).
- [x] 12 reproducible cases including one multi-fault challenge case.
- [x] Original baseline and Phase 4 measurements are preserved.
- [x] Context-v0.2 baseline exists for a fair Phase 5 comparison.
- [x] Publishable comparison arms each contain complete 12/12 evidence with no infrastructure errors.
- [x] Headline claim uses only matched-context complete evidence: **0/12 -> 1/12 (+8.33 percentage points VRR)**.
- [x] Incomplete reviewer recovery remains unscored (`verified_resolution_rate=null`).

### Reproducibility — 15

- [x] Pinned Python/dbt/DuckDB versions.
- [x] Synthetic local data and DuckDB; no warehouse credentials.
- [x] Reference repairs prove oracle solvability.
- [x] `REPRODUCE.md` contains exact install/evaluation commands and the safe local CLI.
- [x] Raw selected evidence is checked in rather than relying only on retention-limited CI artifacts.
- [x] Source workflow run IDs, evaluation commit SHAs, artifact IDs, and SHA-256 artifact digests are recorded.
- [ ] Record the final merged `main` commit SHA in submission notes.

### Hot Take / Insights — 5

Evidence-backed final insights:

1. **A green pipeline is not a verified pipeline.** Phase 2 includes cases where `dbt build` succeeds while the semantic oracle fails.
2. **Better protocol compliance is not the same as better task success.** Phase 4 improved tool discipline but stayed at 0/12 VRR.
3. **An evaluation can be deterministic and still be invalid if required business context is hidden from the agent.** This motivated context v0.2.
4. **More agentic machinery must earn its place.** Phase 4's verifier loop added latency without VRR gain, and the later semantic reviewer was removed after it failed to produce complete comparable evidence on the zero-budget runtime.

## Evidence-integrity rules

- Never publish a VRR from a partial run.
- Never count an infrastructure timeout as a task failure without labeling it.
- Never compare v0.1 and v0.2 context runs as a controlled agent-only comparison.
- Never expose reference repairs or hidden oracle logic to the repair agent.
- Never rewrite or delete a failed experiment solely because it hurts the final narrative.
- Every final quantitative claim must point to checked-in evidence or an exact reproducible command.
