# Reproducing DriftDoctor

This guide is written for a judge starting from a clean machine. DriftDoctor's benchmark uses synthetic data, dbt Core, DuckDB, and a local Ollama model. No warehouse account or paid model API key is required.

> Final Phase 5 winner and headline VRR are intentionally not frozen in this document until the complete controlled experiment matrix finishes without infrastructure errors.

## 1. Requirements

- Linux or macOS
- Python 3.13 (CI uses 3.13.15)
- Git
- Ollama
- enough RAM/disk to run `qwen2.5-coder:1.5b` locally

The pinned Python dependencies are in `requirements.txt`.

## 2. Clone and install

```bash
git clone https://github.com/AaryaMody1301/DriftDoctor.git
cd DriftDoctor
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install Ollama using its official installation instructions, start the local service, then pull the shared comparison model:

```bash
ollama pull qwen2.5-coder:1.5b
```

Confirm the local API is reachable:

```bash
curl -fsS http://127.0.0.1:11434/api/tags
```

## 3. Validate the benchmark contract

```bash
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
```

Expected smoke-test property:

- all 12 original fixtures fail their external oracle;
- all 12 evaluator-only reference repairs pass their external oracle.

Reference repairs prove benchmark solvability and are never included in an agent workspace.

## 4. Inspect one case

```bash
python scripts/materialize_case.py DD-005 --output .work/DD-005 --force
```

The materialized workspace is a self-contained dbt + DuckDB project. The Phase 5 runner additionally writes `BUSINESS_CONTEXT.md`, which contains only user-visible business rules for the case.

After editing the workspace, grade it externally:

```bash
python scripts/evaluate_case.py DD-005 --workdir .work/DD-005
```

## 5. Reproduce the original baseline

Start Ollama first, then run:

```bash
python scripts/run_baseline.py \
  --model qwen2.5-coder:1.5b \
  --max-steps 14
```

The original v0.1 baseline is historical evidence and used benchmark context v0.1. Do not compare it directly with a context-v0.2 Phase 5 system as if the visible inputs were identical.

## 6. Reproduce the controlled Phase 5 comparison

Each command below materializes the same 12 fixtures, adds the same public context v0.2, uses the same hidden external oracle, and uses the same local model.

```bash
python scripts/run_phase5.py \
  --system context-baseline \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

```bash
python scripts/run_phase5.py \
  --system driftdoctor-no-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

```bash
python scripts/run_phase5.py \
  --system driftdoctor-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

A valid aggregate result must contain:

```json
{
  "complete": true,
  "expected_cases": 12,
  "scored_cases": 12,
  "infrastructure_errors": [],
  "verified_resolution_rate": 0.0
}
```

The numeric VRR shown above is only a JSON-shape example. Use the value actually emitted by the completed run.

If `complete` is false, the run is not eligible for a performance claim. Transport failures are recorded separately rather than silently counted as model failures.

## 7. Evidence locations

Phase 5 results are written to:

```text
benchmark/results/phase5/<system>/
  DD-001.json
  ...
  DD-012.json
  summary.json
```

Each scored case record includes the system/model, incident, VRR pass/fail outcome, root-cause prediction, elapsed time, model-call count, external oracle result, observable trajectory, and final git diff.

## 8. Safety boundary

The benchmark operates only on synthetic local projects. DriftDoctor does not merge, deploy, or modify production systems. A real-world integration should generate an approval-ready patch and require a qualified human to approve consequential changes before deployment.

## 9. Approximate runtime and cost

Model API cost is $0 because the comparison model runs locally through Ollama. CPU runtime varies substantially by host. GitHub-hosted CPU runs can take many minutes per case; the experiment workflow uses a larger job timeout to distinguish slow local inference from task failure.

## 10. Exact versions

The repository pins:

```text
dbt-core==1.11.14
dbt-duckdb==1.11.0
duckdb==1.5.5
```

CI uses Python 3.13. The final submission should cite the exact commit SHA used for the headline evaluation.
