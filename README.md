# DriftDoctor

DriftDoctor is an evidence-first agentic workflow for diagnosing and safely repairing dbt regressions caused by schema, dependency, grain, data-quality, and business-contract drift.

> **Final primary benchmark result:** the Phase 8 **hybrid skill-first entry point** solved **12/12 incidents (100% VRR)** on the frozen context-v0.2 benchmark, versus **0/12** for the matched-context simple-agent baseline. It also classified **12/12 root causes**, used **0 model calls**, averaged **6.99 seconds/case**, and passed the DD-012 multi-fault challenge case. All 12 declared benchmark incidents matched high-confidence repair skills, so the bounded local-model fallback was not needed in this run. This is a measured result on the declared 12-case contract-drift benchmark, **not an open-ended claim that DriftDoctor solves arbitrary dbt incidents**.

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

The skills inspect only the local project, source CSV headers, and `BUSINESS_CONTEXT.md`. They do not import benchmark case IDs, evaluator oracle code, or reference repairs. CI enforces this boundary and runs mutation-style probes with alternative contract/source identifiers and time zones.

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
| Phase 8 skills-only ablation | 12/12 | **12/12 (100%)** | 12/12 (100%) | 0.0 | 7.07s |
| **Phase 8 hybrid entry point (final)** | **12/12** | **12/12 (100% VRR)** | **12/12 (100%)** | **0.0** | **6.99s** |

The resource difference is deliberate: the intervention being measured is moving known, high-confidence repair classes out of repeated model generation and into specialized deterministic skills. The configured local coding model remains the fallback for cases that the skill layer cannot resolve. **All 12 primary benchmark cases were handled by skills, so the final hybrid run used 0 model calls and 0 fallback cases.**

Final Phase 8 workflow run: `33257030328`  
Repair-code evaluation SHA: `0c6cf9b42863db4f45a94add11509988bcaa7815`  
Hybrid artifact ID: `9716167394`  
Hybrid artifact digest: `sha256:b6788eb6ed860c339daf3c822639bfde9e759457c7ac9b7825d9a5e6da3ee030`  
Skills-only artifact ID: `9716167164`  
Skills-only artifact digest: `sha256:404a8d60b1134ed78072421e5710ea1c0e8f19a4d15b4779e61f9c422201c030`

Complete raw hybrid and skills-only case records, trajectories, diffs, evaluator outputs, summaries, and provenance are checked into [`evidence/phase8/`](evidence/phase8/).

## Why the architecture changed

The project intentionally preserves failed experiments:

1. The initial simple-agent baseline produced **0/12** verified repairs.
2. DriftDoctor v0.1 added evidence/retry orchestration but still produced **0/12** and became much slower.
3. The Phase 5 staged workflow improved protocol discipline but solved only **1/12**. Failure analysis showed the 1.5B model often understood the symptom yet emitted an unchanged or technically wrong patch.
4. An extra semantic-review model stage was removed because it added latency/transport risk without a complete publishable improvement.
5. Phase 8 moved recurring high-confidence repairs into specialized skills and kept the LLM only as fallback. The actual hybrid entry point then produced the complete **12/12** primary result without needing fallback inference.
6. A mutation test caught an overly fuzzy derived-field alias after the first 12/12 run. That bug was fixed generically, and the full benchmark + hybrid entry point were rerun on the corrected repair-code SHA before final evidence was frozen.

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

### Reproduce the final hybrid evaluation

```bash
python scripts/run_phase8.py \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

On the frozen benchmark, no skill falls through, so this command completes without contacting a model runtime. For the explicit skills-only ablation:

```bash
python scripts/run_phase8.py --no-fallback \
  --model qwen2.5-coder:1.5b \
  --max-calls 14
```

Inspect:

```text
benchmark/results/phase8/hybrid/summary.json
benchmark/results/phase8/hybrid/DD-001.json ... DD-012.json
benchmark/results/phase8/skills-only/summary.json
```

See [`REPRODUCE.md`](REPRODUCE.md) for the clean-environment procedure and historical comparison commands.

## Evidence and submission material

- [`evidence/phase8/README.md`](evidence/phase8/README.md) — final hybrid + skills-only evidence and provenance
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
