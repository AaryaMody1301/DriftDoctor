# Five-minute submission video plan

Target length: **4:30–4:55**. Use one continuous evidence-first story. Do not spend time listing technology logos.

## 0:00–0:35 — Problem and user

Show a broken dbt project and explain:

- analytics engineers often have to correlate source changes, SQL, tests, dbt artifacts, and business rules before they can safely repair a pipeline;
- a compiling project can still be semantically wrong;
- DriftDoctor's goal is an evidence-backed, locally verified patch that remains under human control.

Briefly show DD-010 or DD-011 as the motivating silent-regression example: Phase 2 demonstrated that `dbt build` can be green while the external semantic oracle still fails.

## 0:35–1:05 — Baseline and metric

Show the benchmark/evidence summary:

- 12 synthetic incidents, including one multi-fault challenge case;
- same `qwen2.5-coder:1.5b` model/environment for the controlled Phase 5 comparison;
- one primary metric: **Verified Resolution Rate (VRR)**;
- a case passes only when the external deterministic oracle succeeds;
- evaluator-only reference repairs prove all cases are solvable.

## 1:05–2:25 — End-to-end verified repair: DD-004

Use **DD-004**, the case the final selected workflow actually solves.

Screen sequence:

1. materialized broken workspace and `BUSINESS_CONTEXT.md`;
2. broken `mart_orders.sql` references the old `stg_orders` model;
3. deterministic evidence collector output;
4. schema-constrained diagnosis;
5. structured patch changing the dependency to `stg_orders_v2` while preserving mart columns;
6. guarded write;
7. successful `dbt build`;
8. external oracle PASS for build, output contract, and absence of stale ref;
9. `evidence/phase5/driftdoctor-no-review/DD-004.json` showing the observable trajectory/diff/evidence.

Do not show or narrate private chain-of-thought. Show only observable instructions, structured model outputs, actions/tool results, diff, and evaluation evidence.

## 2:25–3:20 — Measured comparison

Show this frozen table:

| System | Context | Complete | VRR | Mean model calls | Mean time |
|---|---|---:|---:|---:|---:|
| context baseline | v0.2 | 12/12 | **0/12 (0.00%)** | 11.75 | 39.15s |
| **structured/no review — final** | v0.2 | 12/12 | **1/12 (8.33%)** | 2.58 | 185.21s |
| structured/review | v0.2 | 7/12 scored | **unscored** | partial | partial |

Say explicitly:

- the strict controlled improvement is **+1 verified incident / +8.33 percentage points VRR**;
- the absolute 1/12 result is modest and not production reliability;
- incomplete infrastructure-failed runs do not receive a VRR.

## 3:20–4:05 — Changelog and removed experiment

Show `IMPROVEMENT_CHANGELOG.md` and tell the iteration story:

- frozen free-form baseline;
- executable deterministic benchmark;
- DriftDoctor v0.1: better protocol compliance but still 0/12 and much slower;
- evaluation-context audit and context v0.2;
- structured staged repair reaches the first verified repair;
- semantic reviewer ablation is **removed** from the final system.

For the removed reviewer experiment, state the evidence precisely: the final recovery produced only 7 scored cases; four cases hit local-inference transport timeouts and DD-008 produced no record, so its aggregate is intentionally `verified_resolution_rate=null`. Do not claim that the reviewer had a lower true VRR.

## 4:05–4:35 — Reproducibility and safety

Show:

```bash
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py
python scripts/run_phase5.py --system context-baseline --model qwen2.5-coder:1.5b --max-calls 14
python scripts/run_phase5.py --system driftdoctor-no-review --model qwen2.5-coder:1.5b --max-calls 14
```

Then show `evidence/phase5/manifest.json` and mention:

- pinned dbt/DuckDB versions;
- synthetic local data and DuckDB;
- local Ollama model / no paid model API key;
- all 12 raw baseline and final case records checked into the repository;
- source run IDs, evaluation SHAs, artifact IDs, and artifact digests preserved;
- no automatic production deployment or merge;
- human approval before consequential real-world changes.

## 4:35–4:55 — Biggest contribution and hot take

Use this wording:

> DriftDoctor's biggest contribution is not another coding-agent demo; it is a reproducible way to measure whether evidence selection, structured repair, and verification actually make pipeline repair more reliable—and to remove components when the evidence does not justify them.

Finish with:

> **A green pipeline is not a verified pipeline.** More agentic machinery must earn its place with complete measured evidence.
