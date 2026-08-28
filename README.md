# DriftDoctor

DriftDoctor is an evidence-first agentic workflow for diagnosing and repairing dbt pipeline regressions caused by schema, contract, and semantic drift.

> **Hackathon status:** Phase 1 — evaluation foundation. No performance claims have been made yet; the benchmark is intentionally being frozen before the agent is implemented.

## The user and bottleneck

**Primary user:** analytics engineers and data engineers responsible for dbt projects.

When an upstream schema or business rule changes, the downstream symptom can be far from the root cause. Engineers often have to correlate failing commands, SQL models, tests, lineage, schemas, and recent code changes before they can propose a safe repair. A plausible patch is not enough: it must also preserve existing behavior and be reviewable.

DriftDoctor is designed to turn that manual investigation into a controlled loop:

```text
incident
  -> collect evidence
  -> form a root-cause hypothesis
  -> propose the smallest repair
  -> add/identify a regression check
  -> verify in an isolated local project
  -> produce an approval-ready evidence report
```

The workflow will never merge or deploy a repair automatically. The benchmark uses synthetic local projects and a local DuckDB database so consequential actions remain sandboxed.

## What success means

The primary metric is **Verified Resolution Rate (VRR)**:

```text
VRR = verified solved incidents / total benchmark incidents
```

An incident is counted as solved only when all case-specific oracle checks pass. A convincing explanation without a passing oracle is a failure.

The benchmark currently defines **12 fixed incidents**, including one explicitly challenging multi-fault case. The baseline and final workflow must receive the same incidents and be measured with the same oracle.

See:

- [`docs/PROBLEM.md`](docs/PROBLEM.md) — problem, users, scope, safety boundaries
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — frozen evaluation protocol and fairness rules
- [`benchmark/cases.json`](benchmark/cases.json) — machine-readable benchmark contract
- [`benchmark/README.md`](benchmark/README.md) — case-design and implementation rules
- [`baseline/PROMPT.md`](baseline/PROMPT.md) — frozen simple-agent baseline
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) — evidence-linked project evolution

## Phase plan

1. **Evaluation foundation** — lock problem, baseline, metric, cases, oracle rules.
2. **Synthetic benchmark** — implement the 12 dbt + DuckDB incident fixtures and runner.
3. **Baseline measurement** — run the frozen baseline and preserve every trajectory/result.
4. **DriftDoctor workflow** — evidence collection, diagnosis, patch generation, and deterministic verification.
5. **Experiments** — measure each meaningful workflow change against the same cases.
6. **Submission hardening** — clean-environment reproduction, UI/CLI polish, trajectories, report, and demo.

## Phase 1 validation

Once this branch is checked out, run:

```bash
python scripts/validate_benchmark.py
```

This validates the benchmark contract without installing any third-party dependency.

## Current non-goals

- production deployment or automatic merges
- access to private warehouse data
- broad data-observability monitoring
- arbitrary repository repair outside the benchmarked dbt workflow
- claiming an incident is solved based only on model output

## Research basis

The evaluation design intentionally uses deterministic dbt checks wherever possible. dbt's documentation describes data tests as assertions over resources, unit tests as validation of model logic on static inputs, `dbt build` as running selected resources and tests in DAG order, and artifacts such as `manifest.json` / `run_results.json` as machine-readable project and execution evidence. The benchmark will use those surfaces rather than asking an LLM to grade its own repair.

Relevant references:

- https://docs.getdbt.com/docs/build/data-tests
- https://docs.getdbt.com/docs/build/unit-tests
- https://docs.getdbt.com/reference/commands/build
- https://docs.getdbt.com/reference/artifacts/dbt-artifacts
- https://duckdb.org/docs/stable/clients/python/overview
