# Submission readiness checklist

This checklist maps the final DriftDoctor repository to the hackathon deliverables and rubric. Repository/code/evidence work is complete when the final `main` CI passes. The video recording/upload and HackerEarth form are human-only steps.

## Required deliverables

### 1. Complete solution code and Improvement Changelog

- [x] Final runtime, benchmark, evaluator, safe CLI, and tests are present.
- [x] README identifies the intended user, current bottleneck, practical value, architecture, result, failure mode, and hot takes.
- [x] `IMPROVEMENT_CHANGELOG.md` starts at the simple baseline and preserves every meaningful iteration.
- [x] Failed, removed, incomplete, superseded, and corrected experiments remain visible.
- [x] Agent instructions are included in the baseline prompt and runtime and indexed in `docs/AGENT_TRAJECTORIES.md`.
- [x] Work created before vs during the competition is documented in `docs/COMPETITION_PROVENANCE.md`.
- [x] Project and third-party licensing are documented.

### 2. Reproduction guide

- [x] `REPRODUCE.md` starts from a clean environment.
- [x] Exact setup, test, baseline, final evaluation, held-out agent, and CLI commands are provided.
- [x] Required synthetic/local data and expected outputs are explained.
- [x] Python, dbt, DuckDB, PyYAML, Ollama, and model versions/identity are recorded where applicable.
- [x] Approximate runtime, model download size, and zero paid-API cost are stated.
- [x] Primary result can be reproduced without Ollama because every primary case resolves before agent use.

### 3. Solution video

- [x] `docs/VIDEO_PLAN.md` covers problem, baseline, one end-to-end agent execution, primary comparison, changelog, biggest change, removed experiment, reproducibility, and hot takes.
- [ ] Record a ≤5-minute video.
- [ ] Upload the video to an allowed host.

### 4. Agent trajectories

- [x] `docs/AGENT_TRAJECTORIES.md` indexes every agent used.
- [x] Historical baseline/staged/reviewer observable trajectories are preserved in `evidence/phase5/`.
- [x] Corrected primary skill trajectories are preserved in `evidence/phase8/`.
- [x] Final bounded-agent instructions, candidate action space, response, patch, build output, and evaluator result are preserved in `evidence/phase9/agent-fallback-demo.json`.
- [x] Feedback, retries, removed experiments, and human checkpoints are documented.
- [x] Private chain-of-thought is not claimed or exposed.

## Ground rules

- [x] Prior work vs competition work is explicit.
- [x] Project is MIT licensed and third-party licenses/terms are inventoried.
- [x] All consequential actions occur in a disposable local sandbox.
- [x] The original project is never modified and no automatic push/merge/deployment occurs.
- [x] Human approval is required after local verification.
- [x] Unsupported ambiguity causes human escalation rather than open-ended autonomous editing.
- [x] Use case is legal/ethical and does not make decisions about people.
- [x] Benchmark data is synthetic; no private customer information is used.
- [x] No credential, private key, or production warehouse access is required.
- [x] Every quantitative claim points to durable evidence/provenance.
- [x] Public repository and clean-machine commands give judges enough access to reproduce the result.

## Rubric audit

### Problem & User Value — 15

- [x] Primary user: analytics/data engineers responsible for dbt pipelines.
- [x] Bottleneck: evidence-heavy incident diagnosis plus contract-preserving repair verification.
- [x] Concrete scope: source/schema/type/dependency/grain/data-quality/business-semantic drift.
- [x] README gives the before/after workflow and one-command local path.

### Agent Solution & Engineering — 30

- [x] Broken-state evidence is captured before edits.
- [x] Specialized high-confidence skills handle contract-determined work.
- [x] Guarded edits target existing model/macro files only.
- [x] Generic visible-contract checks run after edits.
- [x] Final agent is purposeful: it resolves one missing-ref ambiguity among observed candidates or abstains.
- [x] Agent cannot invent candidates, create files, deploy, or receive hidden evaluator information.
- [x] Unsupported cases escalate to a qualified human.
- [x] Anti-leakage and mutation/generalization tests cover final runtime behavior.
- [x] Historical weak open-ended model fallback is not imported by the final orchestrator.
- [x] Semantic-review ablation was measured and removed rather than assumed useful.

### End-to-End Quality — 20

- [x] Broken local project → evidence → routing → guarded patch → executable checks → approval-ready report.
- [x] External evaluator catches semantic regressions that a green build can miss.
- [x] Synthetic benchmark prevents production side effects.
- [x] CLI accepts only project-local DuckDB profiles.
- [x] CLI sandbox path/deletion guardrails have regression tests.
- [x] Generated DuckDB binary state is excluded from approval diffs.
- [x] DD-012 challenge case is a verified multi-fault pass.
- [x] Held-out ambiguity case demonstrates skills-only abstention and successful bounded-agent resolution.
- [ ] Demonstrate the held-out agent execution and DD-012 evidence in the recorded video.

### Measured Improvement — 15

- [x] One primary metric: Verified Resolution Rate (VRR).
- [x] 12 fixed matched-context cases including one challenge case.
- [x] Matched-context simple-agent baseline: **0/12 VRR**.
- [x] Intermediate staged LLM workflow: **1/12 VRR**.
- [x] Corrected skill-first benchmark: **12/12 VRR**.
- [x] Final selective-agency no-regression rerun: **12/12 VRR**, 12/12 root causes, 0 model calls, 0 escalations, 6.6403s/case.
- [x] Primary improvement is scoped as **0/12 → 12/12 (+100 percentage points)** on the declared benchmark.
- [x] Held-out agent case is reported separately and not folded into primary VRR.
- [x] Skills-only held-out control failed; bounded agent passed with one model call.
- [x] Incomplete semantic-review experiment remains unscored with null VRR.

### Reproducibility — 15

- [x] Pinned Python/package versions.
- [x] Pinned Ollama version and recorded model tag/ID for the agent trajectory.
- [x] GitHub Actions dependencies are pinned to immutable full SHAs.
- [x] Synthetic local data; no warehouse credentials or paid API.
- [x] Reference repairs prove primary benchmark solvability.
- [x] `REPRODUCE.md` contains exact final, held-out, and historical commands.
- [x] Complete corrected Phase 8 raw records are checked in.
- [x] Phase 9 primary summary and complete final agent trajectory are checked in.
- [x] Run IDs, evaluated SHAs, artifact IDs, artifact digests, and checked-in record hashes are preserved.
- [x] `make verify` provides a single judge-facing verification command.

### Hot Take / Insights — 5

- [x] **A green pipeline is not a verified pipeline.**
- [x] **Better protocol compliance is not the same as task success.**
- [x] **Small models can diagnose better than they patch.**
- [x] **More agentic machinery must earn its place.**
- [x] **A perfect benchmark result still needs mutation/generalization tests.**
- [x] **The best agent improvement was knowing when not to call the model.**

## Repository cleanliness

- [x] `docs/REPOSITORY_MAP.md` identifies active runtime, evaluator, evidence, and historical files.
- [x] Active GitHub Actions are reduced to automatic `submission.yml` and manual `phase9.yml`.
- [x] Obsolete measurement/cleanup workflow definitions are removed from the active Actions menu.
- [x] `SUBMISSION.md` contains copy-ready portal content.
- [x] No open GitHub issues remain.

## Final portal steps

- [ ] Confirm the latest `main` `submission-preflight` run is green.
- [ ] Paste the exact latest passing `main` SHA into `SUBMISSION.md`/the form.
- [ ] Paste the uploaded video URL.
- [ ] Submit the public repository, video, and final project description through HackerEarth.

## Evidence-integrity rules

- Never publish a VRR from a partial run.
- Never count infrastructure timeouts as task failures without labeling them.
- Never compare context v0.1 and v0.2 as a controlled workflow-only comparison.
- Never expose evaluator oracle/reference repairs to the runtime.
- Never hard-code benchmark case IDs into final repair runtime.
- Never fold the held-out agent demonstration into primary VRR.
- Never freeze a perfect score after an independent mutation test exposes a defect; fix generically and rerun.
- Never delete a failed experiment solely because it weakens the narrative.
- Never present local verification as permission to deploy without human review.
