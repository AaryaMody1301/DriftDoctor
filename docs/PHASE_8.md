# Phase 8 — hybrid contract repair skills

Phase 8 addresses the dominant failure mode observed in Phase 5: the 1.5B coding model often understood the symptom but still emitted an unchanged, invalid, or contract-breaking patch.

## Decision

Move high-confidence recurring dbt contract repairs into explicit specialized skills and reserve the coding model for unresolved or novel cases.

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

The skills inspect only existing project files, local input headers, and `BUSINESS_CONTEXT.md`. They do not import benchmark case IDs, evaluator oracle code, or reference repairs.

## Generalization bug caught before final freeze

The first Phase 8 implementation reached 12/12 on the frozen benchmark, but a mutation probe exposed an overly fuzzy derived-field alias: a synthetic `owner_display` contract could be incorrectly sourced from `owner_id` instead of being derived from `given_name` + `family_name`.

The test was **not weakened or removed**. The router was fixed generically so explicit contract derivations outrank fuzzy source aliases. The final nine-test anti-leakage/generalization suite then passed, and both the skills-only ablation and the actual hybrid entry point were rerun across all 12 benchmark cases on the corrected repair-code SHA.

## Final corrected result

Workflow run: `33257030328`

Repair-code evaluation SHA: `0c6cf9b42863db4f45a94add11509988bcaa7815`

Final hybrid artifact:

- ID: `9716167394`
- SHA-256: `b6788eb6ed860c339daf3c822639bfde9e759457c7ac9b7825d9a5e6da3ee030`

Skills-only ablation artifact:

- ID: `9716167164`
- SHA-256: `404a8d60b1134ed78072421e5710ea1c0e8f19a4d15b4779e61f9c422201c030`

| Metric | Final hybrid result |
|---|---:|
| Expected/scored cases | **12/12** |
| Verified repairs | **12/12** |
| Verified Resolution Rate | **100%** |
| Root-cause classification | **12/12 (100%)** |
| Infrastructure errors | **0** |
| Fallback cases | **0** |
| Mean elapsed time | **6.9895s/case** |
| Mean model calls | **0.0** |
| Challenge case DD-012 | **PASS** |

The same run's explicit skills-only ablation also scored 12/12 with 0 model calls, averaging 7.066s/case.

All 12 frozen benchmark incidents matched a high-confidence skill, so the configured model fallback was not invoked by the final hybrid entry point. This is a measured result on the declared contract-drift benchmark; it is **not** evidence that DriftDoctor solves arbitrary or open-ended dbt incidents. The fallback exists for incidents outside those high-confidence patterns.

Raw corrected evidence is checked into both `evidence/phase8/hybrid/` and `evidence/phase8/skills-only/`.

## Controlled comparison

The benchmark/context/oracle remained v0.2 throughout the controlled comparison:

| System | VRR | Root-cause accuracy | Mean model calls/turns | Mean elapsed |
|---|---:|---:|---:|---:|
| matched-context baseline | 0/12 (0%) | 0/12 (0%) | 11.75 | 39.15s |
| Phase 5 staged LLM workflow | 1/12 (8.33%) | 3/12 (25%) | 2.58 | 185.21s |
| Phase 8 skills-only ablation | 12/12 (100%) | 12/12 (100%) | 0.0 | 7.066s |
| **Phase 8 hybrid entry point** | **12/12 (100%)** | **12/12 (100%)** | **0.0** | **6.9895s** |

The resource difference is intentional and is the intervention being measured: Phase 8 replaces repeated model reasoning for known, high-confidence repair classes with inspectable deterministic tools and spends model calls only after those tools fail to resolve the incident.

## What was removed

The extra semantic-review model stage remains removed. Earlier experiments showed that another model call added latency and transport risk without a complete publishable improvement. Phase 8 instead adds discriminating specialized skills and executable verification.

## Main insight

**The best agent improvement was knowing when not to call the model.**

For recurring operational repair patterns, a router plus auditable specialized tools can be faster and more reliable than asking a general coding model to regenerate the same SQL repeatedly. The model is most useful as a fallback for ambiguity, not as the default implementation mechanism for every incident.
