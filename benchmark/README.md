# Benchmark

The benchmark is the source of truth for DriftDoctor's hackathon evaluation. It is intentionally defined before the solution is implemented.

## Contract

[`cases.json`](cases.json) contains 12 fixed incidents. Each case has:

- a stable ID;
- a user-facing incident statement;
- a category and difficulty;
- a hidden implementation fault description;
- a canonical `root_cause_class`;
- deterministic oracle requirements.

During Phase 2, every case will become a self-contained dbt + DuckDB fixture under a case directory. The fixture implementation may add files needed to reproduce the fault, but it must not weaken or change the oracle requirements in `cases.json` merely to improve measured performance.

## Planned Phase 2 case layout

```text
benchmark/
  cases.json
  fixtures/
    DD-001/
      project/          # broken starting dbt project
      oracle/           # external deterministic checks
      expected/         # frozen expected values/config
    ...
  results/
    baseline/
    driftdoctor/
```

`results/` will contain raw machine-readable run records. Aggregate metrics must be recomputable from those records.

## Success rule

A case is solved only if **all** of its oracle checks pass after the agent stops. Diagnosis quality is tracked separately and cannot convert a failed repair into a success.

## Why local dbt + DuckDB

The evaluation needs to be:

- inexpensive;
- reproducible from a clean environment;
- safe to run repeatedly;
- deterministic enough for baseline/final comparison;
- rich enough to expose real schema, dependency, data-quality, and SQL-semantic failures.

A local DuckDB-backed dbt project satisfies those constraints without requiring warehouse credentials or private data.

## Deterministic evidence surfaces

Phase 2 should prefer evidence that can be independently checked:

- dbt command exit codes and logs;
- data-test results;
- unit-test results where appropriate;
- generated dbt artifacts such as `manifest.json` and `run_results.json`;
- custom SQL assertions against the local DuckDB file;
- exact git/working-tree diff;
- fixture-specific file assertions.

## Benchmark integrity rules

1. The same starting fixture is used for baseline and DriftDoctor.
2. The same external oracle grades both systems.
3. The agent never receives `fault` or `root_cause_class` fields during a scored run.
4. Oracle code is not exposed as editable task code during a scored run.
5. Every failed run is retained.
6. A case change after Phase 1 requires a changelog entry explaining why; original results may not be compared as though the benchmark were unchanged.
7. DD-012 is the required challenging case and must be discussed independently in the final report.

## Validate the contract

```bash
python scripts/validate_benchmark.py
```

This uses only the Python standard library.
