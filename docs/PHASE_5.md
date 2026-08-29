# Phase 5 - Controlled experiments

Phase 5 began from a measured negative result: both the original baseline and DriftDoctor v0.1 achieved 0/12 Verified Resolution Rate (VRR), while DriftDoctor v0.1 was substantially slower despite better tool/protocol discipline.

Phase 5 is now complete. The final measured workflow is **`driftdoctor-no-review`**.

## Why the evaluation context is versioned

Trajectory review found cases whose incident text referred to a documented business rule but whose materialized project did not actually contain that documentation. Hidden oracle behavior therefore depended on information unavailable to an honest agent.

Context version **0.2** adds `BUSINESS_CONTEXT.md` to each case workspace. It exposes only the legitimate business contract a real engineer would be expected to have. It does **not** expose oracle implementation, reference repairs, expected hidden query results, or benchmark ground-truth fields.

Because visible task context changed, v0.1 and v0.2 VRR values are not treated as directly comparable measurements of agent architecture.

## Frozen experiment controls

All Phase 5 systems use:

- the same 12 case fixtures and hidden external oracle;
- the same `qwen2.5-coder:1.5b` model;
- temperature 0;
- a 14 model-call/turn cap;
- the same local DuckDB/dbt environment;
- the same `BUSINESS_CONTEXT.md` files.

## A - context-baseline

The Phase 3-style open-ended baseline was rerun with legitimate business context available.

**Complete result:** **0/12 VRR**, 0/12 root-cause accuracy, 11.75 mean model calls, 39.15s mean elapsed, zero infrastructure errors.

Evidence: `evidence/phase5/context-baseline/`.

## B - driftdoctor-no-review — final workflow

The retained workflow is:

1. deterministic dbt/artifact/source evidence collection;
2. schema-constrained diagnosis;
3. schema-constrained complete-file patch proposal;
4. guarded patch application;
5. deterministic `dbt build`;
6. at most one build-error repair if the build creates a concrete new signal.

**Complete result:** **1/12 VRR (8.33%)**, 3/12 root-cause accuracy (25%), 2.58 mean model calls, 185.21s mean elapsed, zero infrastructure errors.

DD-004 was the verified repair. The final system improved the matched-context primary metric by **+1 solved incident / +8.33 percentage points VRR**.

Evidence: `evidence/phase5/driftdoctor-no-review/`.

## C - driftdoctor-review — removed experiment

System B plus an adversarial semantic review and at most one semantic repair was tested to isolate whether another model stage earned its latency/complexity.

The final three-shard recovery did **not** produce a valid aggregate:

- 7/12 cases were scored;
- DD-002, DD-004, DD-005, and DD-007 ended in local-inference transport timeouts;
- DD-008 produced no case record;
- `complete=false`;
- `verified_resolution_rate=null`.

One scored reviewer case, DD-006, passed, but a partial pass count is not a VRR. The experiment is preserved under `evidence/phase5/driftdoctor-review-incomplete/` and is explicitly excluded from performance claims.

The semantic reviewer is therefore **removed from the final workflow**. This is not a claim that its true VRR was lower; it is a decision that a component unable to produce complete comparable evidence on the chosen zero-budget runtime did not earn submission-critical complexity.

## Patch guardrails retained

The final staged workflow rejects:

- writes outside `models/` or `macros/`;
- implausibly short replacements;
- markdown-fenced content;
- placeholder text such as `complete replacement contents`;
- unchanged replacement content.

These are general execution-safety checks and do not encode case answers.

## Selection rule and decision

The predeclared rule was: highest publishable VRR; for ties, prefer fewer model calls and then lower mean elapsed time. A performance claim additionally requires a complete 12/12 aggregate with no infrastructure errors.

`driftdoctor-no-review` is selected because it is the only complete Phase 5 DriftDoctor arm and has the highest publishable matched-context VRR: **1/12 versus 0/12 for the matched baseline**. The reviewer arm is unscored, not assigned an artificial zero.

## Reproduce

```bash
python scripts/run_phase5.py --system context-baseline --model qwen2.5-coder:1.5b --max-calls 14
python scripts/run_phase5.py --system driftdoctor-no-review --model qwen2.5-coder:1.5b --max-calls 14
```

The removed reviewer experiment remains reproducible separately:

```bash
python scripts/run_phase5.py --system driftdoctor-review --model qwen2.5-coder:1.5b --max-calls 14
```

Each command preserves case-level observable trajectory, diff, external oracle result, root-cause prediction, elapsed time, and aggregate summary.
