# Phase 8 final evidence

This directory preserves the complete primary-evaluation evidence for the final high-confidence contract-skill path.

- Frozen benchmark/context: v0.2, 12 cases including DD-012 challenge case.
- Result: 12/12 verified repairs (100% VRR), 12/12 root-cause classification, zero infrastructure errors.
- Mean elapsed time: 7.8794 seconds per case.
- Model calls on these 12 cases: 0. The hybrid product retains the local coding-model path only as fallback for cases not handled by high-confidence skills.
- Workflow run: 33256430999.
- Evaluation SHA: `b0dbe1faddb0979f26421a8976e62780034dc067`.
- Artifact ID: 9715977028.
- Artifact digest: `sha256:e97831f48b273f02ea280ba9ded5ddbbef0169f6201f7748f4dd0c7cf82b0f32`.

`skills-only/` contains all 12 raw case records and `summary.json`. Each record includes the visible repair skills chosen, resulting diff, dbt build evidence, and external evaluator output.

The repair-skill runtime does not import `benchmark/oracles.py`, `benchmark/reference_repairs.py`, or benchmark case IDs. Anti-leakage and mutation-style generalization probes live in `tests/test_repair_skills.py` and run in submission CI.
