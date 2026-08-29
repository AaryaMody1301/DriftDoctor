# DriftDoctor

**DriftDoctor is a selective-agent workflow for diagnosing and safely repairing dbt contract drift.** It uses auditable repair skills when the visible contract determines the edit, a constrained local agent only when one real dependency ambiguity remains, and human escalation instead of open-ended autonomous coding when the workflow cannot verify a safe result.

> **Primary result:** **12/12 verified repairs (100% VRR)** on the frozen 12-case context-v0.2 benchmark, versus **0/12** for the matched-context simple-agent baseline. The final no-regression rerun classified **12/12 root causes**, used **0 model calls**, and averaged **6.64 seconds/case**. All declared primary cases matched deterministic high-confidence skills. This is a result on the published synthetic benchmark—not a claim that DriftDoctor repairs arbitrary dbt projects.
>
> **Agent evidence:** on a separate held-out ambiguous dependency case, the skills-only control failed and escalated; the bounded agent made **one** local model call, selected only from two observed existing candidates, produced a guarded patch, and passed every held-out check. This held-out case is **not part of the primary VRR**. Its trajectory is deliberately reported separately.

## The user and bottleneck

**Primary user:** analytics and data engineers who own dbt projects.

When a source schema, model dependency, data grain, or business rule changes, the visible failure can be far downstream from the cause. Engineers must correlate build output, SQL/YAML, source shape, model references, tests, and documented business rules before making a safe change. A plausible patch or green build is not enough: the repaired output contract must be executable, evidence-backed, and reviewable.

DriftDoctor turns that investigation into a bounded local workflow.

## Final workflow

```text
incident + BUSINESS_CONTEXT.md + local dbt/source evidence
                              |
                              v
                     broken-state dbt build
                              |
                              v
             high-confidence contract repair skills
                              |
                    guarded existing-file edit
                              |
                              v
                  dbt + visible-contract checks
                              |
                   unresolved dependency ambiguity?
                        /                 \
                      no                   yes
                      |                     |
          locally verified result   bounded agent chooses only
                      |              observed candidate or abstains
                      |                     |
                      +----------+----------+
                                 v
                   approval-ready diff and report
                                 |
                    human approval / escalation
```

The final runtime never imports the hidden benchmark oracle or evaluator-only reference repairs.

### Deterministic repair skills

`driftdoctor/repair_skills.py` contains inspectable transformations for:

- source-field rename while preserving a stable downstream alias;
- documented derived fields;
- safe text-to-numeric conversion;
- renamed dbt `ref()` targets;
- SCD/latest-record reduction before joins;
- required identifier filtering;
- categorical mapping plus accepted-values validation;
- macro keyword-interface drift;
- one-current-row grain restoration;
- UTC-to-local reporting dates;
- documented accounting formulas.

### Bounded ambiguity agent

`driftdoctor/ambiguity.py` is intentionally narrow. It runs only when the project contains one missing `ref()` with multiple structurally plausible **existing** model candidates. Its JSON schema permits selecting one observed candidate or `abstain`; it cannot invent a model, rewrite arbitrary SQL, create files, or deploy anything.

When no bounded repair verifies, DriftDoctor marks `human_escalation_required=true`.

## Evaluation

The primary metric is **Verified Resolution Rate (VRR)**:

```text
VRR = cases that pass every external oracle check / attempted cases
```

A confident explanation, a syntactically valid patch, or a green `dbt build` does not count unless every case-specific evaluator check passes.

### Controlled primary comparison

All systems below use the same 12 context-v0.2 fixtures and external evaluator.

| System | Complete | VRR | Root-cause accuracy | Mean model calls/turns | Mean elapsed |
|---|---:|---:|---:|---:|---:|
| matched-context simple-agent baseline | 12/12 | **0/12 (0%)** | 0/12 | 11.75 | 39.15s |
| staged LLM workflow | 12/12 | **1/12 (8.33%)** | 3/12 | 2.58 | 185.21s |
| corrected skill-first benchmark | 12/12 | **12/12 (100%)** | 12/12 | 0.0 | 6.99s |
| **final selective-agency no-regression rerun** | **12/12** | **12/12 (100%)** | **12/12** | **0.0** | **6.64s** |

The resource difference is the intervention: known, contract-determined work moved from repeated free-form generation into specialized tools. The model is reserved for ambiguity rather than used as the default implementation mechanism.

### Separate agent trajectory

The held-out `stg_orders` case contains two observed candidates: active `stg_orders_v2` and historical `stg_orders_archive`.

| Control / system | Result |
|---|---|
| skills only | build failed; human escalation required |
| bounded ambiguity agent | selected `stg_orders_v2`; one model call; build and all held-out checks passed |

Full record: [`evidence/phase9/agent-fallback-demo.json`](evidence/phase9/agent-fallback-demo.json). It is **not** silently added to the 12-case primary score.

## Why the architecture changed

1. The simple-agent baseline scored **0/12**.
2. Evidence collection and retry orchestration improved protocol compliance but still scored **0/12** and became slower.
3. Structured diagnosis/patching reached the first verified repair, but only **1/12**.
4. An extra semantic-review model stage was removed after it produced incomplete evidence and more transport risk.
5. Failure analysis showed the small model often diagnosed the right class but emitted an unchanged or technically wrong patch.
6. Recurring contract-determined repairs moved into explicit skills, producing **12/12**.
7. A mutation test then found a fuzzy-alias generalization bug. The failing test was retained, the router was fixed generically, and the complete benchmark was rerun before evidence was frozen.
8. The final runtime removed the weak open-ended coding fallback, added a one-decision bounded agent for true ambiguity, and escalates everything else.

See [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) for the evidence-linked history.

## Quickstart

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make verify
```

Run DriftDoctor on a disposable local DuckDB dbt project:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md
```

Use only deterministic skills and prohibit model inference:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md \
  --no-fallback
```

The CLI:

- copies the project into a marked disposable sandbox;
- accepts only a project-local DuckDB profile;
- edits only existing model/macro files;
- excludes generated database state from the review diff;
- never modifies the source project, pushes, merges, or deploys;
- writes `driftdoctor-report.json` with the trajectory, checks, diff, and approval state;
- requires human approval even after local verification.

## Reproduce the measured results

Primary final regression—no Ollama required because all 12 cases resolve through skills:

```bash
python scripts/run_phase9_primary.py
```

Held-out bounded-agent trajectory—requires Ollama 0.33.2 and `qwen2.5-coder:1.5b`:

```bash
python scripts/run_agent_fallback_demo.py --model qwen2.5-coder:1.5b
```

Exact setup, historical comparisons, expected outputs, runtime, and cost are in [`REPRODUCE.md`](REPRODUCE.md).

## Judge navigation

- [`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md) — active product vs historical experiment files
- [`docs/RULEBOOK_COMPLIANCE.md`](docs/RULEBOOK_COMPLIANCE.md) — every rubric, ground rule, and deliverable mapped to evidence
- [`docs/AGENT_TRAJECTORIES.md`](docs/AGENT_TRAJECTORIES.md) — representative trajectory for every agent used
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) — baseline, iterations, failures, removed experiment, decisions
- [`REPRODUCE.md`](REPRODUCE.md) — clean-machine procedure
- [`evidence/phase8/`](evidence/phase8/) — complete corrected 12-case raw evidence
- [`evidence/phase9/`](evidence/phase9/) — selective-agency regression summary and held-out agent trajectory
- [`docs/VIDEO_PLAN.md`](docs/VIDEO_PLAN.md) — ≤5-minute demo plan
- [`SUBMISSION.md`](SUBMISSION.md) — copy-ready portal text and last manual steps

## Scope, safety, and provenance

- Benchmark data is synthetic; no credentials or private customer data are required.
- Consequential actions remain in a disposable local sandbox and require a human reviewer.
- The current product is scoped to local DuckDB-backed dbt projects.
- The repository is MIT licensed; third-party licenses are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
- Work added during the competition is documented in [`docs/COMPETITION_PROVENANCE.md`](docs/COMPETITION_PROVENANCE.md).

## Remaining limitation and hot takes

The main product risk is coverage outside the explicit skills and the one supported bounded ambiguity pattern. Novel SQL structures or undocumented business rules should escalate; broader independent holdout evaluation is required before production use.

**Hot take #1:** **A green pipeline is not a verified pipeline.**

**Hot take #2:** **The best agent improvement was knowing when not to call the model.**
