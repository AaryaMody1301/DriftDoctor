# Submission readiness checklist

This checklist maps DriftDoctor's final repository to the hackathon deliverables and rubric. Repository/code/evidence work is complete once the final `main` CI passes; only the human-recorded video and portal form remain outside the repository.

## Required deliverables

- [x] Complete code for benchmark, frozen baseline, specialized skills, hybrid fallback, evaluation harness, and safe judge CLI.
- [x] Improvement Changelog preserves baseline, negative experiments, incomplete experiments, the generalization bug found after the first 12/12 run, and the corrected final architecture decision.
- [x] Clean-environment reproduction guide (`REPRODUCE.md`).
- [x] Corrected final hybrid 12-case trajectories/diffs/oracle outputs preserved under `evidence/phase8/hybrid/`.
- [x] Corrected skills-only ablation preserved under `evidence/phase8/skills-only/`.
- [x] Historical Phase 5 evidence preserved under `evidence/phase5/` rather than overwritten by the better result.
- [x] Phase 8 evidence manifest records corrected workflow run, repair-code SHA, both artifact IDs, and both SHA-256 artifact digests.
- [x] Judge-facing CLI runs the final hybrid skill-first workflow on a disposable copy and emits an approval-ready JSON report.
- [x] CLI sandbox deletion/path safety has regression tests.
- [x] Repair-skill runtime has explicit anti-leakage tests and mutation-style generalization probes.
- [x] Nine Phase 8 anti-leakage/generalization tests passed before the corrected benchmark measurement.
- [x] README contains the final primary metric, scope caveat, failed experiments, safety boundary, and hot takes.
- [x] GitHub Action dependencies are pinned to immutable full commit SHAs.
- [x] Expensive historical/model/performance workflows, including Phase 8 measurement, are manual-only after the final evidence freeze.
- [x] **Final hybrid result frozen: 12/12 verified repairs (100% VRR), 12/12 root-cause accuracy, 0 model calls, 0 fallback cases, 6.9895s/case.**
- [x] Skills-only ablation frozen: 12/12 VRR, 0 model calls, 7.066s/case.
- [x] DD-012 multi-fault challenge case is a verified pass in the final hybrid evidence.
- [ ] At portal submission time, copy the exact latest passing `main` commit SHA into the form.
- [ ] Record/upload the <=5 minute video using `docs/VIDEO_PLAN.md`.
- [ ] Submit repository/video on the hackathon portal.

## Rubric audit

### Problem & User Value — 15

- [x] Primary user: analytics/data engineers responsible for dbt pipelines.
- [x] Bottleneck: evidence-heavy incident diagnosis followed by safe contract-preserving repair verification.
- [x] Concrete scope: source/schema/type/dependency/grain/data-quality/business-semantic drift.
- [x] README gives the before/after workflow and one-command local incident path.

### Agent Solution & Engineering — 30

- [x] Local evidence gathering from dbt/project/source context.
- [x] Specialized high-confidence repair skills for recurring deterministic classes.
- [x] Guarded in-place patching; no arbitrary/new-file escape hatch for the skill path.
- [x] Executable dbt verification and visible-contract checks.
- [x] Bounded Qwen2.5-Coder fallback for cases outside the skill router.
- [x] Human approval remains mandatory for consequential application.
- [x] Hidden oracle/reference repairs are evaluator-only.
- [x] Anti-leakage CI rejects evaluator/case-specific tokens in the final skill runtime.
- [x] Mutation/generalization tests exercise alternative source/model/contract identifiers and time zones.
- [x] Removed semantic reviewer is preserved as evidence that extra agent stages do not automatically help.

### End-to-End Quality — 20

- [x] Broken local dbt project → evidence → routed repair → guarded patch → executable build/checks → approval-ready report.
- [x] External oracle catches silent semantic regressions that a green build can miss.
- [x] Synthetic benchmark prevents production side effects.
- [x] Local CLI never edits the source project or deploys automatically.
- [x] DD-012 challenge case has a durable final hybrid trajectory showing two repair skills in one incident.
- [x] First perfect benchmark implementation was not blindly frozen; a later mutation-test failure was fixed generically and the complete benchmark was rerun on corrected code.
- [ ] Demonstrate the DD-012 repair path in the recorded video.

### Measured Improvement — 15

- [x] One primary metric: Verified Resolution Rate (VRR).
- [x] 12 fixed cases with one multi-fault challenge case.
- [x] Matched-context simple-agent baseline: **0/12 VRR**.
- [x] Intermediate Phase 5 workflow: **1/12 VRR**.
- [x] Corrected final Phase 8 hybrid entry point: **12/12 VRR (100%)**.
- [x] Final hybrid run is complete 12/12 with zero infrastructure errors.
- [x] Primary improvement: **0/12 → 12/12 (+100 percentage points VRR)**.
- [x] Final root-cause accuracy: **12/12 (100%)**.
- [x] Final hybrid resource result: **0 model calls**, **0 fallback cases**, **6.9895s/case**.
- [x] Skills-only ablation: **12/12**, **0 model calls**, **7.066s/case**.
- [x] Incomplete semantic-review experiment remains explicitly unscored.
- [x] README clearly scopes 12/12 to the declared benchmark and does not claim open-ended arbitrary repair capability.

### Reproducibility — 15

- [x] Pinned Python/dbt/DuckDB versions.
- [x] Model-based historical workflows pin post-evaluation Ollama reruns and print runtime/model identity.
- [x] GitHub Actions use full immutable SHAs.
- [x] Synthetic local data; no warehouse credentials/private data.
- [x] Reference repairs prove benchmark solvability.
- [x] Final benchmark requires no Ollama/model runtime because all 12 cases resolve before fallback.
- [x] `REPRODUCE.md` contains exact final hybrid, skills-only, and historical comparison commands.
- [x] Raw corrected final evidence is checked into the repository.
- [x] Corrected source run `33257030328`, repair-code SHA `0c6cf9b42863db4f45a94add11509988bcaa7815`, artifact IDs, and artifact digests are frozen in `evidence/phase8/manifest.json`.
- [x] Unit tests include anti-leakage and mutation-style repair-skill probes.
- [ ] Copy final passing `main` SHA into submission notes.

### Hot Take / Insights — 5

Evidence-backed insights:

1. **A green pipeline is not a verified pipeline.** The benchmark includes cases where compilation succeeds while semantic invariants fail.
2. **Better protocol compliance is not the same as better task success.** Phase 4 improved discipline but stayed at 0/12 VRR.
3. **Small models can diagnose better than they patch.** Phase 5 trajectories include correct-ish diagnoses followed by unchanged or technically invalid SQL edits.
4. **More agentic machinery must earn its place.** The semantic-review stage was removed after it added cost/risk without complete comparable evidence.
5. **A perfect benchmark score still needs adversarial checks.** A mutation test caught a real bug after the first 12/12 run; the result was re-earned on corrected code.
6. **The best agent improvement was knowing when not to call the model.** High-confidence contract repairs are faster and more reliable as specialized tools; model calls are reserved for ambiguity.

## Evidence-integrity rules

- Never publish a VRR from a partial run.
- Never count an infrastructure timeout as a task failure without labeling it.
- Never compare context v0.1 and v0.2 as a controlled workflow-only comparison.
- Never expose evaluator oracle/reference repairs to the runtime.
- Never hard-code benchmark case IDs into the repair-skill runtime.
- Never freeze a perfect benchmark result if an independent mutation/generalization check exposes a defect; fix generically and rerun the complete suite.
- Never delete a failed experiment solely because it weakens the narrative.
- Every quantitative claim must point to checked-in evidence or an exact reproducible command.
