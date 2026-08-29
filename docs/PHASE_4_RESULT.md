# Phase 4 measured result

Phase 4 completed successfully as an execution pipeline, but DriftDoctor v0.1 did **not** improve the primary metric.

## Frozen measurements

| System | Model | VRR | Mean time | Mean model/tool turns | Verifier retries |
|---|---|---:|---:|---:|---:|
| Baseline v0.1 | `qwen2.5-coder:1.5b` | 0/12 (0.0%) | 48.0s/case | 11.8 steps | n/a |
| DriftDoctor v0.1 | `qwen2.5-coder:1.5b` | 0/12 (0.0%) | 211.7s/case | 11.8 model calls | 14 |

Both GitHub Actions measurement workflows completed successfully and uploaded complete case-level evidence artifacts.

## What improved even though VRR did not

Trajectory inspection shows the baseline produced 52 invalid action turns across the 12 cases, while DriftDoctor produced 13. DriftDoctor therefore improved protocol/tool-use reliability substantially, but that improvement did not translate into verified repairs.

## Main failure modes

1. **Patch generation quality.** The 1.5B model sometimes wrote placeholders, rewrote a file without fixing it, or exhausted its call budget without reaching a valid repair.
2. **Verifier without new evidence.** The semantic reviewer correctly requested retries in several cases, but often sent the same weak model back to make the same edit. A retry policy is not useful by itself if it cannot add a new discriminating signal.
3. **Evaluation-context validity.** Several hidden oracles encode business rules that are not exposed anywhere in the scored workspace. DD-010 requires the reporting timezone to be Asia/Kolkata and DD-011 requires positive source refund amounts to be subtracted from net revenue, yet the incident text refers only to a "documented" rule and the materialized project contains no such documentation. This makes those cases partly under-specified for any honest agent.
4. **Auxiliary root-cause metric.** Exact-string root-cause matching is too brittle to interpret as semantic diagnosis accuracy. VRR remains the primary metric.

## Phase 5 response

Phase 5 will preserve these results as a failed iteration, repair the visible-context validity issue without changing hidden oracle expectations, rerun a fair baseline on the revised visible context, and then run controlled ablations of:

- schema-constrained structured outputs;
- staged diagnose -> patch -> verify execution;
- write/patch guardrails;
- verifier present vs absent;
- 1.5B vs 3B model capacity as a separate, explicitly labeled experiment.

Prior v0.1 results remain immutable and will not be compared as if they used the revised visible evaluation context.
