# Phase 5 checked-in evidence

This directory preserves the raw Phase 5 evidence used for the final submission so judges are not dependent on retention-limited CI artifacts.

## Publishable matched-context comparison

| System | Complete | Scored | VRR | Root-cause accuracy | Mean model calls | Mean elapsed |
|---|---:|---:|---:|---:|---:|---:|
| `context-baseline` | yes | 12/12 | 0/12 (0.00%) | 0/12 (0.00%) | 11.75 | 39.15s |
| `driftdoctor-no-review` | yes | 12/12 | 1/12 (8.33%) | 3/12 (25.00%) | 2.58 | 185.21s |

The strict matched-context improvement is **+1 verified incident / +8.33 percentage points VRR**. The absolute result remains modest; this is a measured workflow improvement, not a broad product-reliability claim.

## Removed semantic-review experiment

`driftdoctor-review-incomplete/` preserves the failed recovery experiment. Its aggregate contains 7 scored cases. DD-002, DD-004, DD-005, and DD-007 ended in local-inference transport timeouts; DD-008 produced no case record. The aggregate correctly sets `complete=false` and `verified_resolution_rate=null`, so it is not used in the performance comparison.

Every complete case JSON includes observable trajectory/tool/model outputs, diff, external oracle result, model calls, and timing. No private chain-of-thought is required or included.
