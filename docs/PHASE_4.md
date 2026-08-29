# Phase 4 — DriftDoctor workflow

Phase 4 introduces the workflow being evaluated against the frozen simple-agent baseline. It intentionally keeps the same local model (`qwen2.5-coder:1.5b`) and a 14-model-call cap per case.

## Interventions under test

1. **Deterministic evidence collection** before the first model call.
   - runs `dbt build --profiles-dir .`;
   - parses `target/manifest.json` for resources and first-order dependencies;
   - parses `target/run_results.json` for executed-node status/messages;
   - captures project SQL/YAML/macros;
   - captures small samples of synthetic source CSVs.
2. **Evidence-first hypothesis** rather than broad blind exploration.
3. **Smallest-safe-repair instruction** with explicit downstream-contract preservation.
4. **Adversarial semantic review** when the repair agent declares completion.
5. **Bounded retry feedback**: at most two verifier-triggered retries, and verifier calls consume the same 14-call model budget.
6. **External hidden scoring only after completion** using the unchanged Phase 2 oracle.

## Why artifacts are used

Current dbt documentation describes `manifest.json` as the complete project resource representation and exposes `parent_map` / `child_map` plus node dependency metadata. `run_results.json` records status, timing, messages, and executed-node IDs for completed dbt invocations. These are deterministic evidence surfaces that can reduce context noise without relying on an LLM to infer project structure from scratch.

## Integrity boundary

The in-loop verifier never receives `benchmark/cases.json` ground truth, the Phase 2 oracle implementation, or reference repairs. It sees only evidence a real engineer could observe from the broken/repaired project. The hidden oracle is invoked once by the benchmark runner after the workflow stops.

## Fair comparison

Both baseline v0.1 and DriftDoctor v0.1 use:

- the same `qwen2.5-coder:1.5b` model;
- the same 12 frozen incidents;
- the same materialized starting fixtures;
- the same shell/filesystem policy;
- the same external Phase 2 oracle;
- a 14-model-call cap per case.

DriftDoctor differs only in workflow design and deterministic context/verifier behavior, which are the interventions under evaluation.

## Run

```bash
python scripts/run_driftdoctor.py \
  --model qwen2.5-coder:1.5b \
  --max-model-calls 14 \
  --max-retries 2
python scripts/summarize_driftdoctor.py benchmark/results/driftdoctor
```

## Exit criteria

- [x] deterministic evidence collector
- [x] manifest/run-results context
- [x] evidence-first repair loop
- [x] adversarial semantic verifier
- [x] bounded retry feedback
- [x] same-model-call fairness cap
- [x] full trajectory and evidence capture
- [x] GitHub Actions measurement workflow
- [ ] all 12 DriftDoctor cases measured successfully in CI
- [ ] baseline-vs-DriftDoctor comparison frozen for Phase 5
