# Phase 8 final evidence

This directory preserves the complete corrected Phase 8 evaluation from workflow run `33257030328` at repair-code SHA `0c6cf9b42863db4f45a94add11509988bcaa7815`.

## Final hybrid entry point

- System: `driftdoctor-v4-hybrid`
- Frozen benchmark/context: v0.2, 12 cases including DD-012 challenge case
- Result: **12/12 verified repairs (100% VRR)**
- Root-cause accuracy: **12/12 (100%)**
- Infrastructure errors: **0**
- Fallback cases: **0**
- Mean model calls: **0.0**
- Mean elapsed time: **6.9895s/case**
- Artifact ID: `9716167394`
- Artifact digest: `sha256:b6788eb6ed860c339daf3c822639bfde9e759457c7ac9b7825d9a5e6da3ee030`

All 12 declared benchmark cases matched high-confidence deterministic repair skills, so the hybrid product did not invoke its local-model fallback in this run. That is a resource/result fact for this benchmark, not a claim that arbitrary dbt incidents never require model reasoning.

## Skills-only ablation

`skills-only/` is the no-fallback ablation from the same workflow run. It also scored 12/12 with 0 model calls and averaged 7.066s/case. Its artifact ID is `9716167164` with digest `sha256:404a8d60b1134ed78072421e5710ea1c0e8f19a4d15b4779e61f9c422201c030`.

`hybrid/` and `skills-only/` each contain all 12 raw case records plus `summary.json`. Case records include selected skills, diffs, dbt build evidence, external evaluator checks, timing, root-cause results, fallback usage, and model-call count.

`tests/test_repair_skills.py` contains anti-leakage and mutation/generalization probes. The final corrected run passed all nine tests before either benchmark measurement executed.
