# Evaluation Protocol

This document is the Phase 1 evaluation contract. It is intentionally written before the benchmark fixtures or DriftDoctor agent are implemented so the project cannot quietly move the goalposts after seeing results.

## 1. Primary metric: Verified Resolution Rate

**Verified Resolution Rate (VRR)** is the percentage of fixed benchmark incidents whose complete case oracle passes after the attempted repair.

```text
VRR = solved_cases / attempted_cases * 100
```

A case is **solved** only if every required oracle condition for that case passes. Partial credit is reported separately but does not count toward VRR.

A generated explanation, confident diagnosis, or patch that fails the oracle is not a verified resolution.

## 2. Secondary metrics

These provide useful context but never override VRR:

- **Root-cause accuracy:** exact case-level match against the hidden ground-truth failure class.
- **Regression safety:** percentage of cases where pre-existing unaffected checks still pass after the repair.
- **Human interventions:** number of manual edits/hints required after the run starts.
- **Time to verified result:** wall-clock seconds from start to final verification.
- **Tool calls:** total agent tool invocations.
- **Approximate model cost:** reported when an API with measurable usage is used.
- **Patch size:** changed lines/files, used only as a diagnostic for repair minimality.

## 3. Fixed benchmark

The benchmark contains **12 cases** in [`../benchmark/cases.json`](../benchmark/cases.json). Case IDs, incident statements, ground-truth classes, and oracle requirements are frozen by this Phase 1 contract.

The suite covers:

- source schema changes
- type drift
- dbt dependency/ref changes
- join/grain regressions
- nullability and accepted-value regressions
- macro interface drift
- semantic SQL regressions
- one multi-fault challenge case

The difficult multi-fault case must be reported separately in addition to the aggregate metric.

## 4. Baseline definition

The baseline is one general-purpose coding agent using the frozen prompt in [`../baseline/PROMPT.md`](../baseline/PROMPT.md).

To keep the comparison fair, baseline and DriftDoctor must use:

- the same model/provider for a given comparison run;
- the same benchmark fixture and incident statement;
- the same shell/file-system access;
- the same clean starting commit/state;
- the same maximum wall-clock budget;
- the same maximum model/token budget where the provider exposes one;
- the same network policy;
- the exact same deterministic oracle.

The final workflow may provide **structured context, specialized tools, memory/state, deterministic verification, retry policy, and orchestration** because those are the workflow changes under evaluation. Any material resource difference must be recorded with the result.

## 5. Run protocol

For every case and every evaluated system:

1. Create/reset a clean disposable case working directory.
2. Record the case ID, system version/commit, model, and runtime configuration.
3. Present the frozen incident statement.
4. Start the timer immediately before the agent receives the task.
5. Capture all agent messages, tool requests, tool responses, retries, and human checkpoints.
6. Stop the agent when it declares completion or reaches the resource limit.
7. Run the benchmark oracle **outside the agent**.
8. Record every oracle check, not only the aggregate pass/fail.
9. Save the final diff and execution artifacts.
10. Reset the fixture before the next system/case run.

No failed case may be manually repaired and then counted as an agent success.

## 6. Oracle design

Each case defines deterministic `oracle_checks`. The executable benchmark implements those checks as a combination of:

- expected `dbt build`/targeted dbt command success;
- dbt data tests;
- custom SQL assertions against DuckDB for business invariants;
- file/configuration assertions where the exact project structure matters.

The evaluator, not the agent, decides success.

## 7. Root-cause scoring

The benchmark retains a machine-readable `root_cause_class`. Root-cause accuracy is scored only from the agent's final structured diagnosis, before exposing the ground truth.

A diagnosis is correct when its primary class matches the case's frozen class. Free-form prose similarity is not used as the primary judge.

## 8. Repeated runs

Agentic results can vary. Once the implementation is stable enough to measure, the preferred final report is:

- one full deterministic baseline pass across all 12 cases;
- one full DriftDoctor pass across all 12 cases;
- if time/cost allows, three independent runs per system/case and a separately reported mean plus raw outcomes.

The submission must never hide failed runs. If only one pass is affordable, that limitation must be stated.

## 9. Claim policy

A numerical submission claim is allowed only when the repository contains the raw result records needed to recompute it.

Examples:

- Allowed: "VRR increased from 4/12 to 10/12" when all 24 run records and oracle outputs are present.
- Not allowed: "about 80% more reliable" based on selected screenshots or manually chosen successes.

## 10. Phase 1 exit criteria

Phase 1 is complete when:

- [x] user and bottleneck are explicit;
- [x] primary metric is frozen;
- [x] baseline contract is frozen;
- [x] at least ten evaluation cases are defined;
- [x] a challenging case is defined;
- [x] every case has deterministic oracle requirements;
- [x] benchmark schema can be validated without third-party packages;
- [x] Phase 2 has implemented every fixture and oracle executable.
