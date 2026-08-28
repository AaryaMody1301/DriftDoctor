# DriftDoctor

DriftDoctor is an evidence-first agentic workflow for diagnosing and repairing dbt pipeline regressions caused by schema, contract, and semantic drift.

> **Hackathon status:** Phase 2 - executable synthetic benchmark. The 12-case benchmark and external evaluator now exist; no baseline or DriftDoctor performance claim has been made yet.

## The user and bottleneck

**Primary user:** analytics engineers and data engineers responsible for dbt projects.

When an upstream schema or business rule changes, the downstream symptom can be far from the root cause. Engineers often have to correlate failing commands, SQL models, tests, lineage, schemas, and recent code changes before they can propose a safe repair. A plausible patch is not enough: it must preserve existing behavior and be reviewable.

DriftDoctor is designed around a controlled loop:

```text
incident
  -> collect evidence
  -> form a root-cause hypothesis
  -> propose the smallest repair
  -> add/identify a regression check
  -> verify in an isolated local project
  -> produce an approval-ready evidence report
```

The workflow will never merge or deploy a repair automatically. Benchmark actions stay inside synthetic local dbt projects backed by DuckDB.

## What success means

The primary metric is **Verified Resolution Rate (VRR)**:

```text
VRR = verified solved incidents / total benchmark incidents
```

An incident counts as solved only when all case-specific oracle checks pass. A convincing explanation or a green compile alone is not enough.

## Phase 2 quickstart

```bash
python -m pip install -r requirements.txt
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
```

Materialize one broken incident:

```bash
python scripts/materialize_case.py DD-005 --output .work/DD-005 --force
```

Grade it externally after a repair attempt:

```bash
python scripts/evaluate_case.py DD-005 --workdir .work/DD-005
```

The benchmark contains 12 frozen incidents spanning schema drift, type drift, dependency changes, join/grain regressions, data-quality drift, macro interface drift, timezone semantics, business logic, and a multi-fault challenge case.

See:

- [`docs/PROBLEM.md`](docs/PROBLEM.md) - problem, users, scope, safety boundaries
- [`docs/EVALUATION.md`](docs/EVALUATION.md) - frozen evaluation protocol and fairness rules
- [`docs/PHASE_2.md`](docs/PHASE_2.md) - executable benchmark architecture and exit criteria
- [`benchmark/cases.json`](benchmark/cases.json) - machine-readable benchmark contract
- [`benchmark/README.md`](benchmark/README.md) - materialization, oracle, and integrity rules
- [`baseline/PROMPT.md`](baseline/PROMPT.md) - frozen simple-agent baseline
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) - evidence-linked project evolution

## Phase plan

1. **Evaluation foundation** - lock problem, baseline, metric, cases, oracle rules. **Complete.**
2. **Synthetic benchmark** - implement the 12 dbt + DuckDB incident fixtures and evaluator. **Complete pending CI confirmation.**
3. **Baseline measurement** - run the frozen baseline and preserve every trajectory/result.
4. **DriftDoctor workflow** - evidence collection, diagnosis, patch generation, and deterministic verification.
5. **Experiments** - measure each meaningful workflow change against the same cases.
6. **Submission hardening** - clean-environment reproduction, UI/CLI polish, trajectories, report, and demo.

## Current non-goals

- production deployment or automatic merges
- access to private warehouse data
- broad data-observability monitoring
- arbitrary repository repair outside the benchmarked dbt workflow
- claiming an incident is solved based only on model output

## Research basis

The evaluator follows dbt's documented testing semantics: data tests are SQL assertions that pass when they return zero failing rows. Semantic invariants that are not well represented by generic tests are checked directly against the local DuckDB database. DuckDB's Python client supports file-backed local databases, which makes every case reproducible without external warehouse infrastructure.
