# DriftDoctor

DriftDoctor is an evidence-first agentic workflow for diagnosing and safely repairing dbt regressions caused by schema, dependency, grain, data-quality, and business-contract drift.

> **Final primary benchmark result:** the Phase 8 high-confidence repair-skill path solved **12/12 incidents (100% VRR)** on the frozen context-v0.2 benchmark, versus **0/12** for the matched-context simple-agent baseline. It also classified **12/12 root causes**, used **0 model calls**, averaged **7.88 seconds/case**, and passed the DD-012 multi-fault challenge case. This is a measured result on the declared 12-case contract-drift benchmark, **not an open-ended claim that DriftDoctor solves arbitrary dbt incidents**.

## User and bottleneck

**Primary user:** analytics/data engineers responsible for dbt projects.

When a source schema or business rule changes, the downstream symptom can be far from the cause. An engineer may need to correlate build failures, SQL/YAML, source shape, model references, grain, tests, and documented business rules before proposing a safe patch. A plausible patch is insufficient: it must preserve the contract, pass executable checks, and remain reviewable.

DriftDoctor turns that incident workflow into a bounded local repair loop.

## Final architecture

```text
incident + BUSINESS_CONTEXT.md + local dbt/source evidence
              |
              v
   high-confidence repair-skill router
              |
              v
       guarded in-place patch
              |
              v
 dbt build + visible contract checks
              |
       unresolved/ambiguous?
          /           \
        no             yes
        |               |
        |      bounded qwen2.5-coder:1.5b fallback
        |               |
        +-------+-------+
                v
      approval-ready diff/report
                |
                v
          human approval
```

The benchmark-only external oracle is evaluator-side and is never available to the repair runtime.

### Specialized repair skills

`driftdoctor/repair_skills.py` contains auditable skills for recurring high-confidence classes:

- source-field rename while preserving a downstream alias;
- documented derived fields;
- safe text-to-numeric conversion;
- renamed dbt `ref()` targets;
- SCD/latest-record reduction before joins;
- required identifier filtering;
- categorical mapping plus accepted-values validation;
- macro keyword-interface changes;
- current-record grain repair;
- UTC-to-local reporting-date conversion;
- documented accounting formulas.

The skills inspect only the local project, source CSV headers, and `BUSINESS_CONTEXT.md`. They do not import benchmark case IDs, evaluator oracle code, or reference repairs. CI enforces this boundary and runs mutation-style probes with alternative names and time zones.

## What success means

The primary metric is **Verified Resolution Rate (VRR)**:

```text
VRR = externally verified solved incidents / attempted incidents
```

A case is solved only when every case-specific external oracle check passes. A convincing explanation or a green dbt build alone does not count.

## Controlled results

All rows below use the same 12 frozen context-v0.2 fixtures and the same external oracle.

| System | Complete | VRR | Root-cause accuracy | Mean model calls | Mean elapsed |
|---|---:|---:|---:|---:|---:|
| matched-context simple-agent baseline | 12/12 | **0/12 (0%)** | 0/12 (0%) | 11.75 | 39.15s |
| Phase 5 staged LLM workflow | 12/12 | **1/12 (8.33%)** | 3/12 (25%) | 2.58 | 185.21s |
| **Phase 8 specialized-skill path** | **12/12** | **12/12 (100% VRR)** | **12/12 (100%)** | **0.0** | **7.88s** |

The resource difference is deliberate: the intervention being measured is moving known, high-confidence repair classes out of repeated model generation and into specialized deterministic skills. The configured local coding model remains the fallback for cases that the skill layer cannot resolve, but **all 12 primary benchmark cases were handled by skills, so the frozen primary run used 0 model calls**.

Phase 8 workflow run: `33256430999`  
Evaluation SHA: `b0dbe1faddb0979f26421a8976e62780034dc067`  
Artifact ID: `9715977028`  
Artifact digest: `sha256:e97831f48b273f02ea280ba9ded5ddbbef0169f6201f7748f4dd0c7cf82b0f32`

Complete raw case records, trajectories, diffs, evaluator outputs, summary, and provenance are checked into [`evidence/phase8/`](evidence/phase8/).

## Why the architecture changed

The project intentionally preserves failed experiments:

1. The initial simple-agent baseline produced **0/12** verified repairs.
2. DriftDoctor v0.1 added evidence/retry orchestration but still produced **0/12** and became much slower.
3. The Phase 5 staged workflow improved protocol discipline but solved only **1/12**. Failure analysis showed the 1.5B model often understood the symptom yet emitted an unchanged or technically wrong patch.
4. An extra semantic-review model stage was removed because it added latency/transport risk without a complete publishable improvement.
5. Phase 8 moved recurring high-confidence repairs into specialized skills and kept the LLM only as fallback. That path produced the complete **12/12** primary result.

This is the main engineering contribution: use model reasoning where ambiguity exists, and use deterministic tools where the contract already determines the safe transformation.

## Quickstart

```bash
python -m pip install -r requirements.txt
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
```

Run DriftDoctor on a disposable copy of a local dbt project:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md
```

The default is the **hybrid** workflow: deterministic skills first, then bounded local-model fallback only if needed. To prohibit model inference entirely:

```bash
python scripts/run_incident.py \
  --project /path/to/local/dbt-project \
  --incident "Describe the broken pipeline behavior" \
  --business-context /path/to/business-rules.md \
  --no-fallback
```

The command operates on a marked disposable sandbox, never modifies the source project, never deploys/merges automatically, and writes `driftdoctor-report.json` containing the repair path, build evidence, diff, fallback usage, and explicit human-approval requirement.

### Reproduce the final primary evaluation

No model runtime is required for the frozen Phase 8 skills-only path:

```bash
python scripts/run_phase8.py --no-fallback \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Then inspect:

```text
benchmark/results/phase8/skills-only/summary.json
benchmark/results/phase8/skills-only/DD-001.json ... DD-012.json
```

See [`REPRODUCE.md`](REPRODUCE.md) for the clean-environment procedure and historical comparison commands.

## Evidence and submission material

- [`evidence/phase8/README.md`](evidence/phase8/README.md) — final primary evidence and provenance
- [`docs/PHASE_8.md`](docs/PHASE_8.md) — architecture decision and measured result
- [`REPRODUCE.md`](REPRODUCE.md) — clean-environment reproduction
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — evaluation contract and fairness rules
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) — baseline, experiments, failures, and decisions
- [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) — rubric/deliverable audit
- [`docs/VIDEO_PLAN.md`](docs/VIDEO_PLAN.md) — <=5-minute evidence-first demo plan
- [`benchmark/cases.json`](benchmark/cases.json) — frozen 12-case contract
- [`baseline/PROMPT.md`](baseline/PROMPT.md) — frozen simple-agent baseline

## Scope and safety

Current non-goals:

- production deployment or automatic merges;
- private warehouse access;
- arbitrary repository repair outside the dbt workflow;
- claiming success from model output alone;
- claiming the 12/12 benchmark result proves open-ended generalization.

The judge-facing CLI requires a project-local profile, works on a disposable copy, blocks unsafe sandbox deletion, and requires human approval before any patch is applied to the original project.

## Failure mode and hot takes

The remaining product risk is **coverage outside the declared high-confidence skills**. Novel SQL shapes or undocumented business rules may fall through to the small local-model fallback, whose earlier measured repair quality was weak. The correct next production step would be broader independent holdout evaluation, not claiming the current synthetic benchmark is exhaustive.

**Hot take #1:** **a green pipeline is not a verified pipeline.**

**Hot take #2:** **the best agent improvement was knowing when not to call the model.** A reliable workflow should route deterministic, well-specified work to specialized tools and spend model calls only on genuine ambiguity.
