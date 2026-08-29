# Reproducing DriftDoctor

This guide is written for a judge starting from a clean machine. DriftDoctor's benchmark uses synthetic data, dbt Core, DuckDB, and a local Ollama model. No warehouse account or paid model API key is required.

**Final measured workflow:** `driftdoctor-no-review` on public context v0.2. The checked-in matched-context result is **1/12 VRR (8.33%)** versus **0/12** for `context-baseline`.

## 1. Requirements

- Linux or macOS
- Python 3.13; submission CI uses **3.13.15**
- Git
- Ollama; post-evaluation rerun workflows pin **0.33.2**
- enough RAM/disk to run `qwen2.5-coder:1.5b` locally

The Python runtime dependencies are pinned in `requirements.txt`.

## 2. Clone and install

```bash
git clone https://github.com/AaryaMody1301/DriftDoctor.git
cd DriftDoctor
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For a controlled rerun, install the same Ollama version pinned by the manual measurement workflows:

```bash
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.33.2 sh
ollama --version
```

Start Ollama, then pull and record the comparison model identity:

```bash
ollama pull qwen2.5-coder:1.5b
ollama list
```

Confirm the local API is reachable:

```bash
curl -fsS http://127.0.0.1:11434/api/tags
```

### Historical runtime note

The publishable Phase 5 measurement was run in GitHub Actions run `33236007203` from evaluation head `a135e543b6feb15a6003a73aabfdc54b5f37d256`. That historical job used the official Ollama installer without an explicit version and did **not** print `ollama --version`, so this repository does not pretend the exact historical Ollama CLI version was recorded. The stable `0.33.2` release was available at evaluation time; post-evaluation manual workflows pin `0.33.2` and print both the Ollama version and model listing so future runs cannot silently drift. This hardening does not change the frozen result records.

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

The materialized workspace is a self-contained dbt + DuckDB project. Phase 5 additionally writes `BUSINESS_CONTEXT.md`, which contains only user-visible business rules for the case.

After editing the workspace, grade it externally:

```bash
python scripts/evaluate_case.py DD-005 --workdir .work/DD-005
```

## 5. Run DriftDoctor safely on a local project

The judge-facing CLI operates on a disposable copy and never edits the source project. The source project must include `dbt_project.yml` and a project-local `profiles.yml`. Do not put production credentials in the project used for the demo.

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "The upstream customer name column changed and the mart no longer builds" \
  --business-context /path/to/business-rules.md
```

The command prints a sandbox path under `.work/` and writes `driftdoctor-report.json`. The report contains the incident, model/runtime configuration, observable structured trajectory, final dbt build result, git diff, infrastructure status, and explicit human-approval requirement. It performs no deployment and leaves the source project unchanged.

Safety behavior:

- a custom sandbox may not contain the source project or live inside it;
- `--force` only replaces a directory marked as a sandbox previously created by DriftDoctor; it refuses to delete an arbitrary existing directory;
- exit code `0` means `dbt build` passed but **still requires human approval and semantic checks**;
- exit code `1` means the attempted repair did not reach a successful build;
- exit code `2` means local model transport failed.

The CLI defaults to no semantic reviewer because `driftdoctor-no-review` is the selected measured workflow. `--semantic-review` exists only to reproduce the removed experiment.

## 6. Reproduce the original historical baseline

Start Ollama first, then run:

```bash
python scripts/run_baseline.py \
  --model qwen2.5-coder:1.5b \
  --max-steps 14
```

The original v0.1 baseline is historical evidence and used benchmark context v0.1. Do not compare it directly with a context-v0.2 Phase 5 system as if the visible inputs were identical.

## 7. Reproduce the final matched-context comparison

Both commands below materialize the same 12 fixtures, add the same public context v0.2, use the same hidden external oracle, use the same local model, and enforce the same 14-call/turn ceiling.

Matched baseline:

```bash
python scripts/run_phase5.py \
  --system context-baseline \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Final DriftDoctor workflow:

```bash
python scripts/run_phase5.py \
  --system driftdoctor-no-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Expected checked-in reference summaries:

```text
evidence/phase5/context-baseline/summary.json
evidence/phase5/driftdoctor-no-review/summary.json
```

Reference results:

```text
context-baseline          0/12 VRR (0.00%)
driftdoctor-no-review     1/12 VRR (8.33%)
```

A valid result must have `complete=true`, `expected_cases=12`, `scored_cases=12`, no infrastructure errors, and a non-null `verified_resolution_rate`.

## 8. Reproduce the removed reviewer experiment

```bash
python scripts/run_phase5.py \
  --system driftdoctor-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

This is **not** the final workflow. The final recovery attempt is preserved under `evidence/phase5/driftdoctor-review-incomplete/`. It produced 7 scored cases and sets `verified_resolution_rate=null` because transport timeouts/missing evidence prevented a valid 12/12 aggregate. Do not turn its one observed pass into a VRR.

## 9. Evidence locations

```text
evidence/phase5/
  README.md
  manifest.json
  context-baseline/
    DD-001.json ... DD-012.json
    summary.json
  driftdoctor-no-review/
    DD-001.json ... DD-012.json
    summary.json
  driftdoctor-review-incomplete/
    partial DD-*.json records
    summary.json
```

Each complete case record includes the system/model, incident, pass/fail outcome, root-cause prediction, elapsed time, model-call count, external oracle result, observable trajectory, and final git diff.

`evidence/phase5/manifest.json` records source workflow run IDs, evaluation commit SHAs, artifact IDs, and SHA-256 artifact digests. The selected result therefore does not depend on expiring Actions artifacts.

## 10. Safety boundary

The benchmark operates only on synthetic local projects. The judge-facing CLI works on a disposable local copy. DriftDoctor does not merge, deploy, or modify production systems. A real-world integration should generate an approval-ready patch and require a qualified human to approve consequential changes before deployment.

## 11. Runtime and cost

Model API cost is **$0** because the comparison model runs locally through Ollama. CPU runtime varies substantially by host. In the recorded matched-context run:

- context baseline mean elapsed: about **39.15s/case**;
- final DriftDoctor mean elapsed: about **185.21s/case**.

The final workflow trades additional local inference time for structured diagnosis/patching and deterministic build feedback. The repository does not claim that the current runtime is production-optimal.

## 12. Exact pinned software

```text
Python submission CI: 3.13.15
dbt-core==1.11.14
dbt-duckdb==1.11.0
duckdb==1.5.5
post-evaluation rerun Ollama: 0.33.2
model tag: qwen2.5-coder:1.5b
```

GitHub Actions used by the repository are pinned to full immutable commit SHAs, with the human-readable major version left only as an inline comment. The exact measured evaluation/artifact provenance is in `evidence/phase5/manifest.json`.
