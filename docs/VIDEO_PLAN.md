# Five-minute submission video plan

Target length: **4:30–4:55**. Tell one evidence-first story; do not spend time listing technology logos.

## 0:00–0:30 — Problem and user

Show a broken dbt project and say:

- analytics/data engineers must correlate source changes, SQL, tests, grain, and business rules before safely repairing a pipeline;
- a compiling project can still be semantically wrong;
- DriftDoctor produces an evidence-backed patch in a disposable local workspace and leaves the final decision to a human.

Use the project hot take immediately: **a green pipeline is not a verified pipeline.**

## 0:30–1:00 — Baseline and evaluation contract

Show `benchmark/cases.json` / `docs/EVALUATION.md`:

- 12 frozen synthetic dbt + DuckDB incidents;
- one multi-fault challenge case, DD-012;
- one primary metric: **Verified Resolution Rate (VRR)**;
- a case counts only when every external oracle check passes;
- the matched-context simple-agent baseline scored **0/12**.

Mention that evaluator-only reference repairs prove each case is solvable and are never placed in the repair workspace.

## 1:00–2:15 — End-to-end challenge repair: DD-012

Use **DD-012** because it exercises two independent faults and the final hybrid entry point passes it.

Screen sequence:

1. materialize DD-012 and show `BUSINESS_CONTEXT.md`;
2. show the source headers: the name field changed and revenue is now text;
3. show the broken staging SQL still referencing the old name and multiplying text by `1.0`;
4. run the final hybrid workflow;
5. show the router selecting `source_alias` + `safe_numeric`;
6. show the guarded in-place diff: new source name aliased back to the stable public contract and `TRY_CAST(... AS DECIMAL(18,2))` for safe numeric conversion;
7. show successful `dbt build`;
8. show the external oracle PASS for all DD-012 checks;
9. show `evidence/phase8/hybrid/DD-012.json`.

Say explicitly: this benchmark case used **0 model calls** because the high-confidence skill path resolved it before fallback. The product still has a bounded coding-model fallback for unresolved/ambiguous cases.

## 2:15–3:05 — Measured comparison

Show this table:

| System | Complete | VRR | Root-cause accuracy | Mean model calls/turns | Mean time |
|---|---:|---:|---:|---:|---:|
| matched-context simple-agent baseline | 12/12 | **0/12 (0%)** | 0/12 | 11.75 | 39.15s |
| Phase 5 staged LLM workflow | 12/12 | **1/12 (8.33%)** | 3/12 | 2.58 | 185.21s |
| Phase 8 skills-only ablation | 12/12 | **12/12 (100%)** | **12/12** | **0.0** | **7.066s** |
| **Phase 8 hybrid entry point** | **12/12** | **12/12 (100%)** | **12/12** | **0.0** | **6.9895s** |

State the scope carefully:

- primary matched-context improvement: **0/12 → 12/12 VRR (+100 percentage points)**;
- all 12 declared benchmark incidents matched high-confidence skills, so the model fallback was not invoked;
- this is **not an open-ended claim** that DriftDoctor can repair arbitrary dbt projects.

Show `evidence/phase8/manifest.json` with:

- run `33257030328`;
- repair-code SHA `0c6cf9b42863db4f45a94add11509988bcaa7815`;
- hybrid artifact `9716167394` + digest;
- skills-only artifact `9716167164` + digest.

## 3:05–3:55 — The improvement changelog

Show `IMPROVEMENT_CHANGELOG.md` and tell the evidence-driven story:

1. baseline: 0/12;
2. v0.1: more evidence/retries but still 0/12 and slower;
3. context validity audit: make genuinely documented business rules visible;
4. Phase 5 staged model workflow: first verified repair, but only 1/12;
5. semantic-review ablation: incomplete/unscored and removed;
6. failure analysis: the small model often understood the symptom yet emitted an unchanged or incorrect patch;
7. Phase 8: route recurring, contract-determined repairs into explicit specialized skills and keep the model only as fallback;
8. **important integrity moment:** the first 12/12 implementation failed a mutation test for an unseen `owner_display` derivation. We kept the failing test, fixed the router generically, and reran the entire benchmark before freezing the result.

Show one old model failure briefly, such as DD-003 choosing an invalid `DECIMAL(2,1)` cast, then the final skill using DuckDB `TRY_CAST(... AS DECIMAL(18,2))`.

## 3:55–4:30 — Anti-leakage, reproducibility, safety

Show:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/submission_preflight.py
python scripts/run_phase8.py --model qwen2.5-coder:1.5b --max-calls 14
```

Mention:

- all nine repair-skill anti-leakage/generalization tests passed before the final measurement;
- runtime code contains no benchmark case IDs/evaluator imports;
- final raw hybrid + skills-only evidence is checked into `evidence/phase8/`;
- pinned dbt/DuckDB/Python and immutable GitHub Action SHAs;
- synthetic local data, no warehouse credentials or paid API;
- judge CLI works only on a disposable sandbox;
- no automatic merge/deploy and human approval remains required.

## 4:30–4:55 — Biggest contribution and hot takes

Use this wording:

> DriftDoctor's biggest contribution is the routing decision: use models for ambiguity, but turn recurring, contract-determined repairs into inspectable tools and verify the result externally.

Finish with both insights:

> **A green pipeline is not a verified pipeline.**
>
> **The best agent improvement was knowing when not to call the model.**
