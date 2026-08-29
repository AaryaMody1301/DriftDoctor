# Phase 8 — hybrid contract repair skills

Phase 8 addresses the dominant failure mode observed in Phase 5: the 1.5B coding model often understood the symptom but still emitted an unchanged, invalid, or contract-breaking patch.

## Decision

Move high-confidence, recurring dbt contract repairs into explicit specialized skills and reserve the coding model for unresolved or novel cases.

The final product path is therefore:

```text
incident + BUSINESS_CONTEXT.md + local project/source evidence
  -> high-confidence repair-skill router
  -> guarded in-place patch
  -> dbt build + deterministic visible-contract checks
  -> if unresolved: bounded qwen2.5-coder:1.5b fallback
  -> approval-ready diff/report
  -> human approval
```

The benchmark-only external oracle runs after the workflow and is never available to the repair runtime.

## Specialized skills

`driftdoctor/repair_skills.py` contains reusable transformations for:

- stable downstream aliases after source-column rename;
- documented derived display fields;
- safe text-to-numeric conversion using `TRY_CAST`;
- renamed dbt `ref()` targets;
- latest-record/SCD dimension reduction before joins;
- required identifier filtering;
- categorical mapping plus accepted-values validation;
- macro keyword-interface changes;
- current-record grain selection;
- UTC-to-local reporting-date conversion;
- documented accounting formulas.

The skills inspect only existing project files, local input headers, and `BUSINESS_CONTEXT.md`. They do not import benchmark case IDs, evaluator oracle code, or reference repairs. `tests/test_repair_skills.py` contains an explicit anti-leakage check and mutation-style probes using names/zones that are not present in the frozen benchmark.

## Frozen primary result

Workflow run: `33256430999`

Evaluation head SHA: `b0dbe1faddb0979f26421a8976e62780034dc067`

Artifact ID: `9715977028`

Artifact SHA-256: `e97831f48b273f02ea280ba9ded5ddbbef0169f6201f7748f4dd0c7cf82b0f32`

| Metric | Result |
|---|---:|
| Expected/scored cases | 12/12 |
| Verified repairs | **12/12** |
| Verified Resolution Rate | **100%** |
| Root-cause classification | **12/12 (100%)** |
| Infrastructure errors | **0** |
| Mean elapsed time | **7.8794s/case** |
| Mean model calls | **0.0** |
| Challenge case DD-012 | **PASS** |

All 12 frozen benchmark incidents matched a high-confidence skill, so the model fallback was not invoked in this primary run. This is a measured result on the declared contract-drift benchmark; it is **not** evidence that the skills solve arbitrary or open-ended dbt incidents. The hybrid fallback exists specifically for cases outside those high-confidence patterns.

Raw evidence is checked into `evidence/phase8/skills-only/`.

## Controlled comparison

The benchmark/context/oracle remained v0.2 throughout the controlled comparison:

| System | VRR | Root-cause accuracy | Mean model calls | Mean elapsed |
|---|---:|---:|---:|---:|
| matched-context baseline | 0/12 (0%) | 0/12 (0%) | 11.75 | 39.15s |
| Phase 5 staged LLM workflow | 1/12 (8.33%) | 3/12 (25%) | 2.58 | 185.21s |
| **Phase 8 specialized-skill path** | **12/12 (100%)** | **12/12 (100%)** | **0.0** | **7.88s** |

The resource difference is intentional and is the intervention being measured: Phase 8 replaces repeated model reasoning for known, high-confidence repair classes with inspectable deterministic tools. The coding model remains available only when those tools cannot confidently complete the repair.

## What was removed

The extra semantic-review model stage remains removed. Earlier experiments showed that another model call added latency and transport risk without a complete publishable improvement. Phase 8 instead adds discriminating, deterministic repair skills and executable verification.

## Main insight

**The best agent improvement was knowing when not to call the model.**

For recurring operational repair patterns, a small router plus auditable specialized tools can be faster and more reliable than asking a general coding model to regenerate the same SQL repeatedly. The model is most useful as a fallback for ambiguity, not as the default implementation mechanism for every incident.
