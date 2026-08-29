# Reproducing DriftDoctor

This guide is for a judge starting from a clean machine. The benchmark is synthetic and local: dbt Core + DuckDB, with no warehouse credentials and no paid API key.

**Final primary evaluation:** `driftdoctor-v4-skills-only` on context v0.2 scored **12/12 verified repairs (100% VRR)** versus **0/12** for the matched-context simple-agent baseline. The measured Phase 8 path used **0 model calls** because every declared benchmark case matched a high-confidence specialized repair skill. The product keeps `qwen2.5-coder:1.5b` only as bounded fallback for unresolved cases.

## 1. Requirements

- Linux or macOS
- Python 3.13; submission CI uses **3.13.15**
- Git
- no Ollama installation is required to reproduce the final Phase 8 skills-only result
- Ollama is required only to reproduce historical model-based experiments or exercise the hybrid fallback

Pinned Python dependencies are in `requirements.txt`:

```text
dbt-core==1.11.14
dbt-duckdb==1.11.0
duckdb==1.5.5
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

## 3. Validate the frozen benchmark

```bash
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py --timeout 90
```

Expected properties:

- exactly 12 benchmark cases;
- exactly one challenge case, DD-012;
- every original broken fixture fails its external oracle;
- every evaluator-only reference repair passes its oracle.

Reference repairs exist only to prove benchmark solvability. They are not placed in the repair workspace.

## 4. Reproduce the final primary Phase 8 evaluation

```bash
python scripts/run_phase8.py \
  --no-fallback \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

The model name/max-call arguments are retained in the result contract for comparability, but `--no-fallback` guarantees the measured final path never contacts a model runtime.

Expected aggregate:

```text
complete=true
expected_cases=12
scored_cases=12
solved=12
verified_resolution_rate=1.0
root_cause_correct=12
root_cause_accuracy=1.0
mean_model_calls=0.0
infrastructure_errors=[]
```

Measured CI reference:

```text
workflow run: 33256430999
evaluation head: b0dbe1faddb0979f26421a8976e62780034dc067
artifact ID: 9715977028
artifact SHA-256: e97831f48b273f02ea280ba9ded5ddbbef0169f6201f7748f4dd0c7cf82b0f32
mean elapsed: 7.879416666666667 seconds/case
```

Durable evidence:

```text
evidence/phase8/
  README.md
  manifest.json
  skills-only/
    DD-001.json ... DD-012.json
    summary.json
```

Every case record includes the selected repair skills, generated diff, dbt build evidence, external oracle checks, elapsed time, root-cause result, and model-call count.

## 5. Verify anti-leakage/generalization guards

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/submission_preflight.py
```

`tests/test_repair_skills.py` enforces that the repair-skill runtime contains no benchmark case IDs or evaluator/reference-repair imports. It also exercises mutation-style examples with source names, model names, measures, and time zones that are not the frozen benchmark values.

The workflow runtime reads only:

- the incident description;
- the local dbt project;
- local source CSV headers/samples;
- `BUSINESS_CONTEXT.md`.

`benchmark/oracles.py` and `benchmark/reference_repairs.py` are evaluator-side only.

## 6. Run the actual hybrid product on a local project

The judge-facing CLI operates on a disposable copy and never edits the source project. The source project must contain `dbt_project.yml` and a project-local `profiles.yml` suitable for a local/sandbox target.

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md
```

Default behavior:

1. inspect visible project/source/business-contract evidence;
2. route matching high-confidence patterns through deterministic repair skills;
3. run dbt build and visible contract checks;
4. if unresolved, invoke the bounded local coding-model fallback;
5. write an approval-ready `driftdoctor-report.json`;
6. leave the original project unchanged and perform no deployment.

To prohibit model inference entirely:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md \
  --no-fallback
```

Safety behavior:

- a custom sandbox may not contain the source project or live inside it;
- `--force` replaces only a directory carrying DriftDoctor's sandbox ownership marker;
- exit code `0` means the sandbox build passed, but human approval/project-specific semantic checks are still required;
- exit code `1` means the attempted repair did not reach a successful build;
- exit code `2` means the optional local-model fallback failed at the inference transport layer.

## 7. Reproduce the matched-context baseline and Phase 5 intermediate system

For these historical model-based measurements, install/start Ollama and pull the comparison model:

```bash
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.33.2 sh
ollama serve
ollama pull qwen2.5-coder:1.5b
ollama list
```

Matched context baseline:

```bash
python scripts/run_phase5.py \
  --system context-baseline \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Phase 5 staged LLM workflow:

```bash
python scripts/run_phase5.py \
  --system driftdoctor-no-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Checked-in historical results:

```text
context-baseline             0/12 VRR (0.00%), 11.75 model turns/case, 39.15s/case
driftdoctor-no-review        1/12 VRR (8.33%), 2.58 model calls/case, 185.21s/case
Phase 8 skills-only         12/12 VRR (100%), 0 model calls/case, 7.88s/case
```

The old semantic-review experiment remains deliberately incomplete/unscored in `evidence/phase5/driftdoctor-review-incomplete/` because it did not produce a valid 12/12 aggregate.

### Historical Ollama provenance note

The publishable Phase 5 run used the official Ollama installer but did not print its exact CLI version. The repository does not invent that historical version. Post-evaluation manual model workflows pin Ollama `0.33.2` and print runtime/model identity.

## 8. Resource comparison

The Phase 8 resource difference is intentional and is the intervention being measured. The baseline spends model turns on every incident; the final high-confidence path routes well-specified recurring repairs to inspectable specialized tools and spends model calls only on cases that fall through the router.

For the primary frozen cases, no fallback was necessary:

```text
baseline mean model turns: 11.75
Phase 5 mean model calls:    2.58
Phase 8 mean model calls:    0.00
```

There is no model API cost in any measured system because the comparison model is local. The final skills-only path also avoids local model inference entirely.

## 9. Evidence integrity

Phase 5 historical evidence is preserved under `evidence/phase5/`; Phase 8 final evidence is preserved under `evidence/phase8/`. The Phase 8 manifest pins the source run, evaluation SHA, artifact ID, and artifact digest so the final claim does not depend on a retention-limited CI artifact.

## 10. Scope

The 12/12 result is a result on the declared synthetic contract-drift benchmark, not proof of arbitrary open-ended dbt repair. The specialized skills intentionally target recurring, high-confidence operational patterns. Incidents outside those patterns route to the model fallback and require broader independent evaluation before production use.
