# Phase 5 - Controlled experiments

Phase 5 begins from a measured negative result: both the original baseline and DriftDoctor v0.1 achieved 0/12 Verified Resolution Rate (VRR). DriftDoctor v0.1 was substantially slower despite better tool/protocol discipline.

## Why the evaluation context is versioned

Trajectory review found cases whose incident text referred to a documented business rule but whose materialized project did not actually contain that documentation. Hidden oracle behavior therefore depended on information unavailable to an honest agent.

Context version **0.2** adds `BUSINESS_CONTEXT.md` to each case workspace. It exposes only the legitimate business contract a real engineer would be expected to have. It does **not** expose oracle implementation, reference repairs, expected hidden query results, or benchmark ground-truth fields.

Because visible task context changed, v0.1 and v0.2 VRR values must not be treated as directly comparable measurements of agent architecture.

## Experiment matrix

All Phase 5 systems use:

- the same 12 case fixtures and hidden oracle;
- the same `qwen2.5-coder:1.5b` model;
- temperature 0;
- a 14 model-call/turn cap;
- the same local DuckDB/dbt environment;
- the same `BUSINESS_CONTEXT.md` files.

### A - context-baseline

The Phase 3 open-ended baseline is rerun with the legitimate business context available and explicitly discoverable.

Purpose: measure how much of the previous failure came from missing task information alone.

### B - driftdoctor-no-review

A staged workflow:

1. deterministic dbt/artifact/source evidence collection;
2. schema-constrained diagnosis;
3. schema-constrained complete-file patch proposal;
4. guarded patch application;
5. deterministic `dbt build`;
6. one build-error repair if necessary.

Purpose: test structured output + staged execution without paying for a semantic-review model call.

### C - driftdoctor-review

System B plus an adversarial semantic review and at most one semantic repair.

Purpose: isolate whether review adds measurable VRR or merely latency.

## Patch guardrails

The staged workflow rejects:

- writes outside `models/` or `macros/`;
- implausibly short replacements;
- markdown-fenced content;
- placeholder text such as `complete replacement contents`;
- unchanged replacement content.

These are general execution-safety checks and do not encode case answers.

## Selection rule

The Phase 5 winner is chosen primarily by VRR. If two systems tie, prefer fewer model calls and lower mean elapsed time. Semantic review is removed if it does not improve VRR.

## Reproduce

```bash
python scripts/run_phase5.py --system context-baseline
python scripts/run_phase5.py --system driftdoctor-no-review
python scripts/run_phase5.py --system driftdoctor-review
```

Each command preserves case-level trajectory, diff, external oracle result, root-cause prediction, elapsed time, and aggregate summary.
