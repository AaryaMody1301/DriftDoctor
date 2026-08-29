# DriftDoctor

DriftDoctor is an evidence-first agentic workflow for diagnosing and repairing dbt pipeline regressions caused by schema, contract, and semantic drift.

> **Hackathon status:** Phases 1-4 are complete and preserved, Phase 5 controlled experiments are running on context v0.2, and Phase 6 submission hardening is active. The benchmark remains 12 frozen cases with an external deterministic oracle. Final Phase 5 winner/VRR claims remain gated on every comparison arm completing without infrastructure errors.

## The user and bottleneck

**Primary user:** analytics engineers and data engineers responsible for dbt projects.

When an upstream schema or business rule changes, the downstream symptom can be far from the root cause. Engineers often have to correlate failing commands, SQL models, tests, lineage, schemas, and recent code changes before they can propose a safe repair. A plausible patch is not enough: it must preserve existing behavior and be reviewable.

DriftDoctor is designed around a controlled loop:

```text
incident
  -> collect evidence
  -> form a root-cause hypothesis
  -> propose the smallest repair
  -> verify executable behavior
  -> produce an approval-ready evidence report
```

The workflow never merges or deploys a repair automatically. Benchmark actions stay inside synthetic local dbt projects backed by DuckDB, and the judge-facing CLI operates on a disposable copy of a local project.

## What success means

The primary metric is **Verified Resolution Rate (VRR)**:

```text
VRR = verified solved incidents / total benchmark incidents
```

An incident counts as solved only when all case-specific oracle checks pass. A convincing explanation or a green compile alone is not enough.

## Current measured evidence

The corrected context-v0.2 experiment is intentionally reported only when an arm completes all 12 cases with zero infrastructure errors.

- `context-baseline`: completed all 12 cases; final comparison report will be frozen with the full Phase 5 result set.
- `driftdoctor-no-review`: completed all 12 cases with **1/12 verified resolutions (8.33% VRR)** and **3/12 root-cause classifications correct**, with zero infrastructure errors.
- `driftdoctor-review`: measurement is still in progress; no final winner is claimed yet.

These are experiment results for the pinned local `qwen2.5-coder:1.5b` configuration, not general product reliability claims.

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

The command writes an approval-ready `driftdoctor-report.json` containing the structured trajectory, build evidence, diff, and explicit human-approval requirement. It never modifies the source project and performs no deployment.

Materialize one benchmark incident:

```bash
python scripts/materialize_case.py DD-005 --output .work/DD-005 --force
```

Grade it externally after a repair attempt:

```bash
python scripts/evaluate_case.py DD-005 --workdir .work/DD-005
```

Run one Phase 5 comparison arm with local Ollama:

```bash
python scripts/run_phase5.py --system driftdoctor-no-review --model qwen2.5-coder:1.5b --max-calls 14
```

The benchmark contains 12 frozen incidents spanning schema drift, type drift, dependency changes, join/grain regressions, data-quality drift, macro interface drift, timezone semantics, business logic, and a multi-fault challenge case.

See:

- [`REPRODUCE.md`](REPRODUCE.md) - clean-environment reproduction, safe CLI, and evidence guide
- [`docs/PROBLEM.md`](docs/PROBLEM.md) - problem, users, scope, safety boundaries
- [`docs/EVALUATION.md`](docs/EVALUATION.md) - frozen evaluation protocol and fairness rules
- [`docs/PHASE_2.md`](docs/PHASE_2.md) - executable benchmark architecture and exit criteria
- [`docs/PHASE_4_RESULT.md`](docs/PHASE_4_RESULT.md) - preserved failed workflow experiment
- [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) - judge-facing deliverable/rubric audit
- [`docs/VIDEO_PLAN.md`](docs/VIDEO_PLAN.md) - evidence-first <=5 minute demo plan
- [`benchmark/cases.json`](benchmark/cases.json) - machine-readable benchmark contract
- [`benchmark/README.md`](benchmark/README.md) - materialization, oracle, and integrity rules
- [`baseline/PROMPT.md`](baseline/PROMPT.md) - frozen simple-agent baseline
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) - evidence-linked project evolution

## Phase plan

1. **Evaluation foundation** - lock problem, baseline, metric, cases, oracle rules. **Complete.**
2. **Synthetic benchmark** - implement the 12 dbt + DuckDB incident fixtures and evaluator. **Complete.**
3. **Baseline measurement** - run the frozen baseline and preserve trajectories/results. **Complete.**
4. **DriftDoctor workflow** - implement and measure the first evidence/repair loop; preserve the negative result. **Complete.**
5. **Controlled experiments** - compare context baseline, no-review, and semantic-review workflows under context v0.2. **Measurement in progress.**
6. **Submission hardening** - clean-environment reproduction, judge CLI, evidence packaging, safety documentation, report, and demo. **In progress.**

## Current non-goals

- production deployment or automatic merges
- access to private warehouse data
- broad data-observability monitoring
- arbitrary repository repair outside the benchmarked dbt workflow
- claiming an incident is solved based only on model output

## Failure mode and current hot take

The main observed failure mode is **repair quality after diagnosis**: structured evidence and protocol guardrails can make an agent more disciplined without making the generated patch correct. Phase 4 demonstrated that verifier retries alone did not improve VRR.

**Hot take:** a green pipeline is not a verified pipeline. For repair agents, executable verification and explicit business contracts matter more than adding agent count; the final Phase 5 ablation will determine whether the semantic reviewer earns its complexity.

## Research basis

The evaluator follows dbt's documented testing semantics: data tests are SQL assertions that pass when they return zero failing rows. Semantic invariants that are not well represented by generic tests are checked directly against the local DuckDB database. DuckDB's Python client supports file-backed local databases, which makes every case reproducible without external warehouse infrastructure.
