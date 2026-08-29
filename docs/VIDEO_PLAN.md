# Five-minute submission video plan

Target length: 4:30–4:55. Use one continuous story with evidence on screen. Do not spend time listing technology logos.

## 0:00–0:35 — Problem and user

Show a broken dbt project and say:

- analytics engineers often have to correlate source changes, SQL, tests, dbt artifacts, and business rules before they can safely repair a pipeline;
- a compiling project can still be semantically wrong;
- DriftDoctor's goal is an evidence-backed, locally verified patch that remains under human control.

Show DD-011 or DD-010 briefly as the motivating silent-regression example.

## 0:35–1:05 — Baseline and metric

Show the benchmark summary:

- 12 synthetic incidents;
- same model/environment for controlled comparisons;
- one primary metric: Verified Resolution Rate;
- a case passes only when the external deterministic oracle succeeds.

Explain that reference repairs are evaluator-only and prove every case is solvable.

## 1:05–2:25 — One end-to-end DriftDoctor run

Use a case that the final selected workflow actually solves.

Screen sequence:

1. materialized broken workspace + `BUSINESS_CONTEXT.md`;
2. deterministic preflight evidence;
3. structured diagnosis;
4. structured minimal patch;
5. guarded write;
6. `dbt build` / visible verification;
7. final hidden-oracle PASS;
8. compact trajectory/diff/evidence record.

Do not show private chain-of-thought. Show only observable inputs, actions, tool results, structured outputs, retries, and final evidence.

## 2:25–3:20 — Measured comparison

Insert final Phase 5 table only after all runs are complete.

Required columns:

| System | Context | VRR | Mean model calls | Mean time |
|---|---|---:|---:|---:|
| context baseline | v0.2 | PENDING | PENDING | PENDING |
| structured/no review | v0.2 | PENDING | PENDING | PENDING |
| structured/review | v0.2 | PENDING | PENDING | PENDING |

Highlight the predeclared selection rule: highest VRR; ties broken by fewer calls and then latency.

## 3:20–4:05 — Changelog and failed experiment

Show the Improvement Changelog and explicitly include Phase 4:

- free-form baseline;
- executable deterministic benchmark;
- evidence-first DriftDoctor v0.1;
- Phase 4 result: better protocol compliance but no VRR gain and much higher latency;
- benchmark-context audit;
- structured-output/staged-repair Phase 5 experiments;
- final retained workflow.

Explain one component that was removed or rejected if Phase 5 evidence supports that decision.

## 4:05–4:35 — Reproducibility and safety

Show:

```bash
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
python scripts/run_phase5.py ...
```

Mention:

- pinned dependencies;
- synthetic data and DuckDB;
- local Ollama model / no paid API key;
- complete case-level trajectories and diffs;
- no automatic production deployment or merge;
- human approval before consequential real-world changes.

## 4:35–4:55 — Contribution + hot take

Freeze wording after final experiment results. Strong candidate framing:

> DriftDoctor's biggest contribution is not another coding-agent demo; it is a reproducible way to measure whether evidence selection, structured repair, and verification actually make pipeline repair more reliable.

Candidate insight:

> More agentic machinery did not automatically help. The first verifier loop increased cost and latency without increasing verified success; reliability improved only when the workflow and evaluation exposed the right evidence and enforced executable outcomes.

Use only claims supported by final artifacts.
