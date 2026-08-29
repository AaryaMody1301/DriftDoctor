# Phase 9 evidence — selective agency

Phase 9 closes the main submission gap left by Phase 8: the fixed 12-case benchmark was solved entirely by deterministic repair skills, so the primary score did not exercise the model-backed agent. The final product now uses an agent only for a narrow decision that rules cannot safely make.

## Primary regression

`primary-summary.json` records a complete rerun of the frozen context-v0.2 benchmark through the final selective-agency entry point:

| Metric | Result |
|---|---:|
| Cases scored | 12/12 |
| Verified repairs | 12/12 |
| VRR | 100% |
| Root-cause correct | 12/12 |
| Model calls | 0 |
| Agent cases | 0 |
| Human escalations | 0 |
| Mean elapsed | 6.6403s/case |

This confirms that the safety and routing changes did not regress the final benchmark result. It does **not** show the agent was needed on those 12 cases.

## Representative bounded-agent trajectory

`agent-fallback-demo.json` is a separately evaluated held-out ambiguity case. It is intentionally not included in the primary VRR.

The broken mart references a removed `stg_orders` model. Two existing candidates are visible:

- `stg_orders_v2` — documented as the active dependency;
- `stg_orders_archive` — documented as a historical snapshot.

The deterministic skill layer correctly abstains because two candidates are structurally plausible; the skills-only control remains broken and requests human escalation. The bounded agent receives only the incident, business context, downstream SQL, and the two observed candidates. Its JSON schema permits selecting one candidate or `abstain`—it cannot invent a model name. In the recorded run it selected `stg_orders_v2`, the guarded patch was applied, dbt build passed, visible contract checks passed, and the external held-out evaluator passed every check.

| Metric | Result |
|---|---:|
| Skills-only build | failed (return code 2) |
| Skills-only escalation | required |
| Agent model calls | 1 |
| Agent selection | `stg_orders_v2` |
| Bounded mode | `bounded_ambiguity_resolver` |
| Agent case verified | yes |
| Human escalation after agent | no |
| Elapsed | 19.89s |

## Provenance

See `manifest.json` for:

- workflow run `33259014887`;
- evaluated source SHA `33caefca6a5a003090edea1ba6cc5d3cc0bd2dbc`;
- artifact IDs and SHA-256 digests;
- checked-in record hashes;
- model/runtime identity.

The source workflow artifacts expire, so the compact primary summary and complete representative agent trajectory are committed here as durable evidence.
