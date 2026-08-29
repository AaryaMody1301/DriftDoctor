# Reproducing DriftDoctor

This guide is written for a judge starting from a clean machine. DriftDoctor uses synthetic local data, dbt Core, and DuckDB. The primary final benchmark requires no warehouse account, private credential, paid model API, or model runtime.

## Results to reproduce

### Primary frozen benchmark

The final selective-agency entry point processes the same 12 context-v0.2 incidents used by the matched baseline:

```text
complete=true
expected_cases=12
scored_cases=12
solved=12
verified_resolution_rate=1.0
root_cause_correct=12
model_calls=0
agent_cases=0
escalation_cases=0
mean_elapsed_seconds=6.640333333333333
```

The matched-context simple-agent baseline is 0/12 VRR. The historical staged LLM workflow is 1/12 VRR.

### Representative agent trajectory

A separate held-out ambiguous dependency case demonstrates the final bounded agent:

```text
skills-only build return code=2
skills-only human escalation=true
agent model calls=1
fallback_mode=bounded_ambiguity_resolver
selected candidate=stg_orders_v2
held-out evaluator passed=true
elapsed_seconds=19.89
```

This case is not included in the 12-case primary VRR.

## 1. Requirements

- Linux or macOS
- Python 3.13; CI uses **3.13.15**
- Git
- approximately 1 GB free disk only when reproducing the optional local-agent trajectory
- Ollama **0.33.2** and `qwen2.5-coder:1.5b` only for model-based historical runs or the held-out agent case

Pinned Python packages:

```text
dbt-core==1.11.14
dbt-duckdb==1.11.0
duckdb==1.5.5
PyYAML==6.0.3
```

## 2. Clone and install

```bash
git clone https://github.com/AaryaMody1301/DriftDoctor.git
cd DriftDoctor
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Equivalent shortcut:

```bash
make install
```

## 3. Run tests and integrity gates

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py --timeout 90
python scripts/submission_preflight.py
```

Expected properties:

- all unit, safety, mutation, anti-leakage, and bounded-agent tests pass;
- the benchmark contains exactly 12 cases and one challenge case, DD-012;
- every broken fixture fails its external oracle;
- every evaluator-only reference repair passes;
- final evidence, license inventory, claims, workflow set, and provenance pass preflight.

Run all non-model verification plus the final primary evaluation with:

```bash
make verify
```

## 4. Reproduce the final primary result

```bash
python scripts/run_phase9_primary.py
```

This materializes each synthetic case in a disposable workspace, writes the same public business context, runs the final selective-agency workflow, and grades the result with the external evaluator.

Expected output file:

```text
benchmark/results/phase9/primary-regression/summary.json
```

Expected aggregate is the primary result shown at the top of this guide. All 12 cases are handled by deterministic skills, so this command does not contact Ollama.

### Frozen primary provenance

```text
workflow run: 33259014887
evaluation SHA: 33caefca6a5a003090edea1ba6cc5d3cc0bd2dbc
artifact ID: 9716719953
artifact SHA-256: e41106ab0169566e8492bd0d125956f8cc9d59323aa8071c61ddcc2946753d78
checked-in summary: evidence/phase9/primary-summary.json
```

The full corrected Phase 8 raw 12-case records remain under `evidence/phase8/`; Phase 9 confirms the final safety/agency changes did not regress that result.

## 5. Reproduce the bounded-agent trajectory

Install the pinned local model runtime:

```bash
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.33.2 sh
ollama serve
```

Run `ollama serve` in a separate terminal when it does not start as a service. Then:

```bash
ollama pull qwen2.5-coder:1.5b
ollama --version
ollama list
python scripts/run_agent_fallback_demo.py --model qwen2.5-coder:1.5b
```

Expected output file:

```text
benchmark/results/phase9/agent-fallback-demo.json
```

Expected behavior:

1. the skills-only control abstains, the project remains broken, and escalation is required;
2. the agent sees exactly two observed candidate models plus `abstain` in its output schema;
3. one model call selects `stg_orders_v2` from the documented active-vs-historical context;
4. a deterministic existing-file patch is applied;
5. dbt build and every held-out check pass.

### Frozen agent-trajectory provenance

```text
workflow run: 33259014887
evaluation SHA: 33caefca6a5a003090edea1ba6cc5d3cc0bd2dbc
Ollama: 0.33.2
model: qwen2.5-coder:1.5b
model ID: d7372fd82851
artifact ID: 9716761142
artifact SHA-256: 77a7807842b16193afa23385bbc216794ec382d78e8b2c487d82f53791fc5c4a
checked-in trajectory: evidence/phase9/agent-fallback-demo.json
```

## 6. Run the product CLI safely

The source project must contain:

- `dbt_project.yml`;
- a project-local `profiles.yml` whose active adapter is DuckDB;
- local/synthetic input data appropriate for the project;
- optionally, a business-context Markdown/text file.

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md
```

Deterministic-only mode:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md \
  --no-fallback
```

The command prints the sandbox path and writes `driftdoctor-report.json` containing:

- execution/approval status;
- broken-state and final build evidence;
- selected repair skills;
- bounded-agent decision when used;
- remaining visible-contract concerns;
- reviewable source/config diff;
- explicit human-approval and escalation fields.

Safety guarantees:

- the original project is never modified;
- custom sandboxes cannot contain the source project or live inside it;
- `--force` deletes only a directory carrying DriftDoctor's ownership marker;
- non-DuckDB profiles are refused;
- generated `.duckdb` state is excluded from the approval diff;
- no remote push, merge, deployment, or production connection occurs;
- exit `0` means local checks passed but human approval is still required;
- exit `1` means build/contract verification failed or escalation is required;
- exit `2` means the optional local inference transport failed.

## 7. Inspect one primary benchmark case

```bash
python scripts/materialize_case.py DD-012 --output .work/DD-012 --force
```

Add the public context used by the comparison:

```bash
python - <<'PY'
from pathlib import Path
from benchmark.public_context import write_public_context
write_public_context('DD-012', Path('.work/DD-012'))
PY
```

After an attempted repair, grade externally:

```bash
python scripts/evaluate_case.py DD-012 --workdir .work/DD-012
```

The repair runtime never receives `benchmark/oracles.py`, ground-truth labels, or `benchmark/reference_repairs.py`.

## 8. Reproduce historical comparisons

Start Ollama and pull the model as described above.

Matched-context simple-agent baseline:

```bash
python scripts/run_phase5.py \
  --system context-baseline \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Intermediate staged LLM workflow:

```bash
python scripts/run_phase5.py \
  --system driftdoctor-no-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

The semantic-review experiment remains intentionally incomplete/unscored in `evidence/phase5/driftdoctor-review-incomplete/`; do not convert its partial records into a VRR.

## 9. Evidence locations

```text
evidence/phase5/   matched baseline, staged LLM workflow, removed reviewer
evidence/phase8/   complete corrected 12-case skill-first raw evidence
evidence/phase9/   final no-regression summary and bounded-agent trajectory
```

Every published quantitative claim points to a checked-in record or manifest containing the source run, evaluated SHA, artifact ID, and digest.

## 10. Runtime and cost

- Paid API cost: **$0**.
- Primary final benchmark: about **6.64s/case** mean on the recorded GitHub-hosted CPU run; no model call.
- Held-out bounded-agent case: **19.89s** after runtime/model setup; one local model call.
- Model download: approximately **986 MB** for the pinned tag in the recorded run.
- Clean-machine installation and model download time depend on network and host performance and are not included in the per-case figures.

## 11. Scope

The 12/12 result applies to the declared synthetic contract-drift benchmark. The agent trajectory demonstrates one separately evaluated bounded ambiguity pattern. Neither result proves arbitrary open-ended dbt repair. Unsupported patterns deliberately escalate to a qualified human reviewer.
