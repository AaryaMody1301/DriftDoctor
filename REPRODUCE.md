# Reproducing DriftDoctor

This guide is for a judge starting from a clean machine. The benchmark is synthetic and local: dbt Core + DuckDB, with no warehouse credentials and no paid API key.

**Final primary evaluation:** `driftdoctor-v4-hybrid` on context v0.2 scored **12/12 verified repairs (100% VRR)** versus **0/12** for the matched-context simple-agent baseline. It also scored 12/12 root-cause accuracy, used **0 model calls**, invoked fallback on **0 cases**, and averaged **6.9895s/case**. Every declared benchmark incident matched a high-confidence specialized repair skill, so the configured `qwen2.5-coder:1.5b` fallback was not needed in this run.

## 1. Requirements

- Linux or macOS
- Python 3.13; submission CI uses **3.13.15**
- Git
- no Ollama installation is required to reproduce the frozen Phase 8 result, because no benchmark case falls through to model inference
- Ollama is required only to reproduce historical model-based experiments or exercise a hybrid fallback on an unresolved incident

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

## 3. Validate the frozen benchmark and integrity checks

```bash
python scripts/validate_benchmark.py
python -m unittest discover -s tests -p 'test_*.py'
python scripts/smoke_benchmark.py --timeout 90
python scripts/submission_preflight.py
```

Expected properties:

- exactly 12 benchmark cases;
- exactly one challenge case, DD-012;
- every original broken fixture fails its external oracle;
- every evaluator-only reference repair passes its oracle;
- repair-skill anti-leakage/generalization tests pass;
- final checked-in evidence/provenance and claim hygiene pass submission preflight.

Reference repairs exist only to prove benchmark solvability. They are never placed in the repair workspace.

## 4. Reproduce the final Phase 8 hybrid evaluation

```bash
python scripts/run_phase8.py \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Expected aggregate:

```text
system=driftdoctor-v4-hybrid
complete=true
expected_cases=12
scored_cases=12
solved=12
verified_resolution_rate=1.0
root_cause_correct=12
root_cause_accuracy=1.0
fallback_cases=0
mean_model_calls=0.0
infrastructure_errors=[]
```

Because each frozen case is solved before fallback, this command does not contact a model runtime on the declared benchmark.

For the explicit no-fallback ablation:

```bash
python scripts/run_phase8.py \
  --no-fallback \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Both measurements were executed in the same corrected CI run after all nine generalization/anti-leakage tests passed.

## 5. Frozen final provenance

```text
workflow run: 33257030328
repair-code evaluation SHA: 0c6cf9b42863db4f45a94add11509988bcaa7815

hybrid artifact ID: 9716167394
hybrid artifact SHA-256: b6788eb6ed860c339daf3c822639bfde9e759457c7ac9b7825d9a5e6da3ee030
hybrid mean elapsed: 6.9895 seconds/case

skills-only artifact ID: 9716167164
skills-only artifact SHA-256: 404a8d60b1134ed78072421e5710ea1c0e8f19a4d15b4779e61f9c422201c030
skills-only mean elapsed: 7.066 seconds/case
```

Durable evidence:

```text
evidence/phase8/
  README.md
  manifest.json
  hybrid/
    DD-001.json ... DD-012.json
    summary.json
  skills-only/
    DD-001.json ... DD-012.json
    summary.json
```

Every case record includes the selected repair skills, generated diff, dbt build evidence, external oracle checks, elapsed time, root-cause result, fallback usage, and model-call count.

## 6. Anti-leakage/generalization guard

`tests/test_repair_skills.py` rejects benchmark case IDs/evaluator imports in the repair runtime and contains mutation-style cases using source/model/contract identifiers and time zones outside the frozen benchmark. A mutation test found a real fuzzy-alias bug in the first 12/12 implementation; the bug was fixed generically, then both 12-case measurements were rerun on the corrected SHA above before final evidence was frozen.

The repair runtime reads only:

- the incident description;
- the local dbt project;
- local source CSV headers/samples;
- `BUSINESS_CONTEXT.md`.

`benchmark/oracles.py` and `benchmark/reference_repairs.py` are evaluator-side only.

## 7. Run the hybrid product on a local project

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

## 8. Reproduce historical comparisons

For historical model-based measurements, install/start Ollama and pull the comparison model:

```bash
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.33.2 sh
ollama serve
ollama pull qwen2.5-coder:1.5b
ollama list
```

Matched-context baseline:

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

Checked-in comparison:

```text
context-baseline             0/12 VRR (0.00%), 11.75 model turns/case, 39.15s/case
driftdoctor-no-review        1/12 VRR (8.33%), 2.58 model calls/case, 185.21s/case
Phase 8 skills-only         12/12 VRR (100%), 0 model calls/case, 7.066s/case
Phase 8 hybrid final        12/12 VRR (100%), 0 model calls/case, 6.9895s/case
```

The old semantic-review experiment remains deliberately incomplete/unscored in `evidence/phase5/driftdoctor-review-incomplete/` because it did not produce a valid 12/12 aggregate.

### Historical Ollama provenance note

The publishable Phase 5 run used the official Ollama installer but did not print its exact CLI version. The repository does not invent that historical version. Post-evaluation manual model workflows pin Ollama `0.33.2` and print runtime/model identity.

## 9. Resource interpretation

The resource difference is intentional. The baseline spends model turns on every incident; the final hybrid router sends well-specified recurring repairs to inspectable specialized tools and reserves model inference for unresolved ambiguity. On the declared benchmark the fallback is never reached, so the measured final system uses fewer model resources, not more.

## 10. Scope

The 12/12 result is a result on the declared synthetic contract-drift benchmark, not proof of arbitrary open-ended dbt repair. The specialized skills intentionally target recurring high-confidence operational patterns. Incidents outside those patterns route to the model fallback and require broader independent evaluation before production use.
