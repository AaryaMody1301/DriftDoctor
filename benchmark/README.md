# Benchmark

The benchmark is the source of truth for DriftDoctor's hackathon evaluation. Its 12 incident contracts were frozen before the agent implementation.

## Executable Phase 2 design

Phase 2 materializes each incident as a disposable dbt project backed by a local DuckDB file. The committed repository stores a deterministic fixture factory instead of twelve copied project trees so shared project configuration cannot drift between cases.

```text
benchmark/
  cases.json                 # frozen public contract
  fixture_factory.py         # broken project + synthetic input generator
  oracles.py                 # external deterministic grader
  reference_repairs.py       # evaluator-only gold repair for smoke tests
scripts/
  materialize_case.py
  evaluate_case.py
  smoke_benchmark.py
```

The **agent workspace contains only the materialized case project**. `oracles.py`, `reference_repairs.py`, `cases.json` ground truth fields, and the parent repository must not be mounted into the agent sandbox during a scored run.

## Install

Python 3.10+ is required by `dbt-duckdb`; CI uses Python 3.13.

```bash
python -m pip install -r requirements.txt
```

The benchmark pins:

- `dbt-core==1.11.14`
- `dbt-duckdb==1.11.0`
- `duckdb==1.5.5`

## Materialize one broken case

```bash
python scripts/materialize_case.py DD-005 --output .work/DD-005 --force
```

The generated directory is a real dbt project with:

- `dbt_project.yml`
- a local `profiles.yml`
- synthetic raw input under `input/`
- `benchmark.duckdb` with those inputs loaded into the `raw` schema
- broken models/macros/tests needed for the incident
- a `.driftdoctor-case` marker used by the external evaluator

You can then work only inside `.work/DD-005`.

## Evaluate one workspace

The evaluator runs outside the workspace:

```bash
python scripts/evaluate_case.py DD-005 \
  --workdir .work/DD-005 \
  --json results/DD-005.json
```

A case passes only when **every** check passes. `dbt build` is necessary but not sufficient: semantic incidents such as timezone drift and refund-sign regressions are also checked with deterministic DuckDB assertions.

## Smoke the entire benchmark

```bash
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
```

For all 12 cases the smoke test proves two properties:

1. the frozen broken fixture does **not** pass its oracle;
2. an evaluator-only reference repair **does** pass the exact same oracle.

That catches impossible cases, accidentally healthy fixtures, and broken evaluator logic before any agent is scored.

## Evidence surfaces

The evaluator intentionally relies on independent evidence:

- `dbt build` exit status and output;
- dbt data tests for structural/data-contract assertions;
- generated dbt artifacts in the materialized project's `target/` directory;
- direct DuckDB SQL assertions for semantic business rules;
- exact file/config assertions for dependency and validation-contract cases.

## Benchmark integrity rules

1. Baseline and DriftDoctor start from separately materialized copies of the same case.
2. The same external oracle grades both systems.
3. The agent receives the public incident text, not the `fault`, `root_cause_class`, oracle implementation, or reference repair.
4. The evaluator directory is outside the editable agent workspace.
5. Every failed run is retained.
6. Case IDs and oracle requirements in `cases.json` remain frozen for benchmark v0.1.0.
7. DD-012 is the required challenging multi-fault case and is reported separately.
8. No result is a success merely because SQL compiles or the agent claims completion.
