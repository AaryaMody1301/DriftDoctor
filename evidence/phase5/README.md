# Phase 5 checked-in evidence

This directory preserves the raw **historical Phase 5** matched-context comparison and removed reviewer experiment. It remains part of the final submission because it explains why the later specialized-skill architecture was necessary; the final primary result is preserved separately under [`../phase8/`](../phase8/).

## Historical matched-context comparison

| System | Complete | Scored | VRR | Root-cause accuracy | Mean model calls | Mean elapsed |
|---|---:|---:|---:|---:|---:|---:|
| `context-baseline` | yes | 12/12 | 0/12 (0.00%) | 0/12 (0.00%) | 11.75 | 39.15s |
| `driftdoctor-no-review` | yes | 12/12 | 1/12 (8.33%) | 3/12 (25.00%) | 2.58 | 185.21s |

Phase 5 improved the matched baseline by **+1 verified incident / +8.33 percentage points VRR**, but the absolute result remained weak. Trajectory analysis from these failures motivated Phase 8's high-confidence specialized repair skills.

## Removed semantic-review experiment

`driftdoctor-review-incomplete/` preserves the failed recovery experiment. Its aggregate contains 7 scored cases. DD-002, DD-004, DD-005, and DD-007 ended in local-inference transport timeouts; DD-008 produced no case record. The aggregate correctly sets `complete=false` and `verified_resolution_rate=null`, so it is not converted into a task score.

Every complete case JSON includes observable trajectory/tool/model outputs, diff, external oracle result, model calls, and timing. No private chain-of-thought is required or included.
