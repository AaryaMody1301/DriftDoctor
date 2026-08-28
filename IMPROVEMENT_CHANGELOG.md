# Improvement Changelog

This file is the evidence-linked evolution log required for the hackathon submission. Scored performance results remain blank until Phase 3 runs the frozen baseline.

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline definition | Freeze one general-purpose coding-agent prompt before implementing DriftDoctor so the comparison cannot be retrofitted to favor the final workflow. | `baseline/PROMPT.md`; benchmark protocol defined before any scored run. Baseline VRR: **not run yet**. | Keep prompt frozen for v0.1 and run all 12 cases in Phase 3. |
| Iteration 1 - evaluation-first foundation | Define the primary metric, 12 incidents, deterministic oracle requirements, fairness rules, and one challenging multi-fault case before agent implementation. | `docs/EVALUATION.md`, `benchmark/cases.json`, `scripts/validate_benchmark.py`. Agent VRR: **not run yet**. | Keep. It prevents moving the goalposts and makes every later change measurable. |
| Iteration 2 - executable benchmark | Materialize each frozen incident as a synthetic dbt + DuckDB workspace and grade repairs with an external deterministic evaluator. Add reference repairs solely to prove every case is solvable and CI to prove each fixture starts broken. | `benchmark/fixture_factory.py`, `benchmark/oracles.py`, `benchmark/reference_repairs.py`, `scripts/smoke_benchmark.py`, GitHub Actions smoke run. Scored VRR: **not run yet**. | Keep. The evaluator is now independent from the future agent and can catch semantic failures even when `dbt build` is green. |
| Iteration 3 | Not started. | Not measured. | Pending Phase 4/5 experiment. |
| Final | Not started. | Not measured. | Pending final evaluation. |

## Candidate experiments to test, not assumed improvements

These are hypotheses for later phases. They must not be described as improvements until benchmark evidence supports them.

1. Structured evidence collection from dbt logs/artifacts vs. free-form repository exploration.
2. Lineage-aware context selection vs. broad context loading.
3. External deterministic verification vs. agent self-assessment.
4. Verification-triggered retry with failure feedback vs. one-shot completion.
5. Single repair agent with strong tools vs. extra agent orchestration.

At least one experiment that fails to help, or makes performance worse, should remain in this changelog because the hackathon brief explicitly values what was learned from removed experiments.
