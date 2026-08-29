# DriftDoctor

DriftDoctor is an evidence-first agentic workflow for diagnosing and repairing dbt pipeline regressions caused by schema, contract, dependency, and semantic drift.

> **Final measured workflow:** `driftdoctor-no-review` on benchmark context v0.2. It solved **1/12 incidents (8.33% VRR)** versus **0/12** for the matched-context baseline. The optional semantic reviewer is **not** part of the final system because its recovery experiment remained infrastructure-incomplete and therefore has no publishable VRR.

## The user and bottleneck

**Primary user:** analytics engineers and data engineers responsible for dbt projects.

When an upstream schema or business rule changes, the downstream symptom can be far from the root cause. Engineers often have to correlate failing commands, SQL models, tests, lineage, schemas, business contracts, and recent code changes before they can propose a safe repair. A plausible patch is not enough: it must preserve intended behavior and be reviewable.

DriftDoctor turns that incident workflow into a bounded local loop:

```text
incident + documented business context
  -> deterministic evidence collection
  -> schema-constrained diagnosis
  -> schema-constrained minimal patch
  -> guarded write
  -> deterministic dbt build feedback
  -> at most one build-error repair
  -> approval-ready report + external evaluation evidence
```

The final measured workflow deliberately omits the extra semantic-review model stage. DriftDoctor never merges or deploys a repair automatically. Benchmark actions stay inside synthetic local dbt projects backed by DuckDB, and the judge-facing CLI operates on a disposable copy of a local project.

## What success means

The primary metric is **Verified Resolution Rate (VRR)**:

```text
VRR = verified solved incidents / total benchmark incidents
```

An incident counts as solved only when all case-specific external oracle checks pass. A convincing explanation or a green compile alone is not enough.

## Final measured evidence

All publishable Phase 5 claims use the same 12 fixtures, context v0.2, `qwen2.5-coder:1.5b`, temperature 0, 14-call/turn ceiling, DuckDB/dbt environment, and hidden external oracle.

| System | Complete | VRR | Root-cause accuracy | Mean model calls | Mean elapsed |
|---|---:|---:|---:|---:|---:|
| `context-baseline` | 12/12 | **0/12 (0.00%)** | 0/12 (0.00%) | 11.75 | 39.15s |
| **`driftdoctor-no-review` (final)** | 12/12 | **1/12 (8.33%)** | 3/12 (25.00%) | 2.58 | 185.21s |
| `driftdoctor-review` | 7/12 scored | **unscored** | unscored | partial only | partial only |

The strict matched-context improvement is **+1 verified incident / +8.33 percentage points VRR**. DD-004 is the verified final-system repair. This is a modest benchmark improvement, not a claim that the current 1.5B local model is production-ready.

The reviewer recovery is preserved as a failed experiment rather than converted into a score. DD-002, DD-004, DD-005, and DD-007 hit local-inference transport timeouts; DD-008 produced no case record. Its aggregate correctly records `complete=false` and `verified_resolution_rate=null`.

Historical context is also preserved: the original context-v0.1 baseline scored 0/12, and DriftDoctor v0.1 also scored 0/12 while becoming much slower. Because visible business context changed between v0.1 and v0.2, those historical scores are not presented as the controlled architecture comparison.

Raw case records, observable trajectories, diffs, oracle outputs, summaries, workflow provenance, artifact IDs, and digests are checked into [`evidence/phase5/`](evidence/phase5/).

## Quickstart

```bash
python -m pip install -r requirements.txt
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
```

Run DriftDoctor against a disposable copy of a local dbt project:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md
```

The command writes an approval-ready `driftdoctor-report.json` containing the observable structured trajectory, build evidence, diff, infrastructure status, and explicit human-approval requirement. It never modifies the source project and performs no deployment.

Reproduce the matched-context comparison with local Ollama:

```bash
python scripts/run_phase5.py \
  --system context-baseline \
  --model qwen2.5-coder:1.5b \
  --max-calls 14

python scripts/run_phase5.py \
  --system driftdoctor-no-review \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

The benchmark contains 12 frozen incidents spanning schema drift, type drift, dependency changes, join/grain regressions, data-quality drift, macro interface drift, timezone semantics, business logic, and one multi-fault challenge case.

## Evidence and documentation

- [`evidence/phase5/README.md`](evidence/phase5/README.md) - checked-in final result evidence and removed reviewer experiment
- [`REPRODUCE.md`](REPRODUCE.md) - clean-environment reproduction and safe CLI
- [`docs/PROBLEM.md`](docs/PROBLEM.md) - problem, users, scope, safety boundaries
- [`docs/EVALUATION.md`](docs/EVALUATION.md) - frozen evaluation protocol and fairness rules
- [`docs/PHASE_4_RESULT.md`](docs/PHASE_4_RESULT.md) - preserved negative workflow experiment
- [`docs/PHASE_5.md`](docs/PHASE_5.md) - controlled ablation and final decision
- [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) - deliverable/rubric audit
- [`docs/VIDEO_PLAN.md`](docs/VIDEO_PLAN.md) - evidence-first <=5 minute demo plan
- [`benchmark/cases.json`](benchmark/cases.json) - machine-readable benchmark contract
- [`baseline/PROMPT.md`](baseline/PROMPT.md) - frozen simple-agent baseline
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) - evidence-linked project evolution, including removed experiments

## Phase plan

1. **Evaluation foundation** - metric, cases, fairness rules, baseline contract. **Complete.**
2. **Synthetic benchmark** - 12 dbt + DuckDB fixtures and external evaluator. **Complete.**
3. **Baseline measurement** - frozen baseline and trajectories. **Complete.**
4. **DriftDoctor v0.1** - evidence/retry workflow measured and preserved as a negative experiment. **Complete.**
5. **Controlled experiments** - matched-context baseline, staged no-review system, semantic-review ablation. **Complete; final workflow frozen.**
6. **Submission hardening** - safe CLI, durable evidence, reproduction guide, CI/preflight, rubric/video plan. **Complete except recording/uploading the manual demo video and submitting on the hackathon portal.**

## Current non-goals

- production deployment or automatic merges
- access to private warehouse data
- broad data-observability monitoring
- arbitrary repository repair outside the benchmarked dbt workflow
- claiming an incident is solved based only on model output

## Research basis

The evaluator follows dbt's documented testing semantics: data tests are SQL assertions that pass when they return zero failing rows. Semantic invariants that are not sufficiently represented by generic tests are checked directly against the local DuckDB database. The benchmark is synthetic and local so judges do not need warehouse credentials or paid model APIs.

## Failure mode and hot take

The main observed failure mode is **repair quality after diagnosis**. Structured evidence and output constraints made the workflow more disciplined and reduced model calls, but the 1.5B local model still generated incorrect repairs on 11/12 cases. The semantic-review experiment also showed an operational failure mode: adding another inference stage can increase latency and transport risk without producing a valid comparable result.

**Hot take:** **a green pipeline is not a verified pipeline.** In repair agents, explicit business contracts and external executable verification matter more than agent count. More agentic machinery must earn its place with complete measured evidence; if it cannot, remove it.
