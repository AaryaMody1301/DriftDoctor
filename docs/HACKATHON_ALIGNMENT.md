# Hackathon Alignment

This repository is organized around the scoring rubric and final deliverables in the micro1 Agentic Workflows Hackathon brief.

| Criterion | Points | Final DriftDoctor evidence |
|---|---:|---|
| Problem & User Value | 15 | `docs/PROBLEM.md` defines the analytics/data engineer, evidence-heavy incident bottleneck, scope, and practical value. |
| Agent Solution & Engineering | 30 | Final v4 hybrid combines visible local context, high-confidence specialized repair skills, guarded in-place patching, executable dbt/contract checks, bounded local-model fallback for unresolved cases, and mandatory human approval. |
| End to End Quality | 20 | `scripts/run_incident.py` runs on a disposable copy and produces an approval-ready JSON report. The final benchmark includes a verified multi-fault DD-012 trajectory under `evidence/phase8/hybrid/`. |
| Measured Improvement | 15 | Frozen v0.2 comparison: matched simple-agent baseline **0/12 VRR**, Phase 5 staged LLM **1/12**, corrected final Phase 8 hybrid **12/12 (100%)**, 12/12 root-cause accuracy, 0 fallback cases, 0 model calls, 6.9895s/case. |
| Reproducibility | 15 | `REPRODUCE.md`, pinned Python/dbt/DuckDB versions, immutable Action SHAs, synthetic DuckDB fixtures, evaluator-only reference repairs, durable raw evidence, run/SHA/artifact provenance, anti-leakage tests, and submission preflight. |
| Hot Take / Insights | 5 | Evidence supports two conclusions: **a green pipeline is not a verified pipeline**, and **the best agent improvement was knowing when not to call the model**. |

## Final deliverable mapping

1. **Complete solution code + Improvement Changelog** — final hybrid runtime plus `IMPROVEMENT_CHANGELOG.md`, which preserves negative, incomplete, superseded, and corrected experiments.
2. **Reproduction guide** — `REPRODUCE.md` contains exact final hybrid, skills-only ablation, historical baseline/system commands, versions, evidence locations, runtime/resource differences, and safety notes.
3. **Solution video (up to 5 minutes)** — `docs/VIDEO_PLAN.md` is a 4:30–4:55 evidence-first storyboard using DD-012, the controlled results, the mutation-test correction, removed reviewer experiment, and final insights.
4. **Agent/workflow trajectories** — `evidence/phase8/hybrid/` contains all 12 final case records with selected skills, diffs, build evidence, oracle results, timings, fallback usage, and model-call counts. Historical model trajectories remain in `evidence/phase5/`.

## Final result provenance

- Final system: `driftdoctor-v4-hybrid`
- Workflow run: `33257030328`
- Repair-code evaluation SHA: `0c6cf9b42863db4f45a94add11509988bcaa7815`
- Hybrid artifact ID: `9716167394`
- Hybrid artifact digest: `sha256:b6788eb6ed860c339daf3c822639bfde9e759457c7ac9b7825d9a5e6da3ee030`
- Verified Resolution Rate: **12/12 (100%)**
- Root-cause accuracy: **12/12 (100%)**
- Model calls: **0**
- Fallback cases: **0**
- Mean elapsed: **6.9895 seconds/case**

The 12/12 result is intentionally scoped to the declared synthetic contract-drift benchmark. It is not presented as proof of arbitrary open-ended dbt repair.

## Guardrails inherited from the brief

- synthetic/local data only for evaluation; no warehouse credentials or private data;
- benchmark oracle/reference repairs remain evaluator-only;
- final skill runtime contains no benchmark case IDs and is checked by anti-leakage tests;
- judge CLI works on a disposable sandbox and never deploys/merges automatically;
- human approval is required before any consequential use of a patch;
- partial/infrastructure-incomplete runs are not converted into scores;
- every quantitative final claim points to checked-in evidence and exact provenance;
- a mutation/generalization test that failed after the first 12/12 run was kept, fixed generically, and followed by a complete corrected rerun before the final result was frozen.
