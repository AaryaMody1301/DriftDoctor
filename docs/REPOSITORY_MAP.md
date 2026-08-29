# Repository map

The repository preserves experiment history, but judges should not have to infer which files are current. This map separates the final product path from historical evidence.

## Start here

| Path | Purpose |
|---|---|
| [`../README.md`](../README.md) | Product, architecture, primary results, quickstart, scope |
| [`../REPRODUCE.md`](../REPRODUCE.md) | Clean-machine reproduction and expected output |
| [`../IMPROVEMENT_CHANGELOG.md`](../IMPROVEMENT_CHANGELOG.md) | Evidence-linked evolution, failures, removed experiments |
| [`RULEBOOK_COMPLIANCE.md`](RULEBOOK_COMPLIANCE.md) | Requirement-by-requirement submission audit |
| [`AGENT_TRAJECTORIES.md`](AGENT_TRAJECTORIES.md) | Index for every agent and representative observable trajectory |
| [`VIDEO_PLAN.md`](VIDEO_PLAN.md) | ≤5-minute recording plan |
| [`../SUBMISSION.md`](../SUBMISSION.md) | Copy-ready portal content and last manual steps |

## Final product runtime

| Path | Status | Responsibility |
|---|---|---|
| `driftdoctor/v4.py` | **active final orchestrator** | Initial build, skill routing, bounded ambiguity agent, verification, escalation |
| `driftdoctor/repair_skills.py` | **active** | High-confidence contract-derived repairs |
| `driftdoctor/contract_checks.py` | **active** | Generic checks derived from visible business context |
| `driftdoctor/ambiguity.py` | **active final agent** | One constrained candidate-selection decision or abstention |
| `driftdoctor/evidence.py` | **active** | Local dbt/project/source evidence collection |
| `scripts/run_incident.py` | **active judge CLI** | Disposable sandbox, DuckDB-only safety, report generation |

The active runtime is explicitly covered by `tests/test_final_runtime_integrity.py`, which rejects benchmark case IDs/evaluator imports and rejects the historical open-ended agent from the final orchestrator.

## Evaluation

| Path | Purpose |
|---|---|
| `benchmark/cases.json` | Frozen 12-case primary benchmark |
| `benchmark/fixture_factory.py` | Synthetic broken project generation |
| `benchmark/oracles.py` | External evaluator; never imported by final runtime |
| `benchmark/reference_repairs.py` | Evaluator-only solvability proof |
| `benchmark/public_context.py` | Legitimate visible business contracts |
| `scripts/run_phase9_primary.py` | Final 12-case selective-agency regression |
| `scripts/run_agent_fallback_demo.py` | Separate held-out bounded-agent trajectory |
| `scripts/submission_preflight.py` | Evidence, claim, workflow, license, and integrity audit |

## Durable evidence

| Path | Meaning |
|---|---|
| `evidence/phase5/` | Matched baseline, staged LLM workflow, incomplete reviewer ablation |
| `evidence/phase8/` | Corrected 12/12 skill-first benchmark records and provenance |
| `evidence/phase9/` | Final no-regression summary plus held-out agent trajectory |

## Historical implementations

These files are retained because the rulebook requires an honest improvement history and representative trajectories for removed/failed agents:

| Path | Historical role |
|---|---|
| `driftdoctor/agent.py` | Phase 4 evidence-first agent |
| `driftdoctor/v2.py` | Phase 5 schema-constrained staged agent/reviewer |
| `driftdoctor/v3.py` | Superseded contract-guided open-ended model prototype |
| `scripts/run_baseline.py` | Historical baseline measurement |
| `scripts/run_phase5.py` | Historical controlled experiment runner |
| `scripts/run_phase7.py` | Superseded model prototype runner |
| `docs/PHASE_2.md` … `docs/PHASE_8.md` | Detailed experiment records |

Historical code is not the default judge path. `scripts/run_incident.py` imports the current v4 workflow.

## Automation

Only two workflows remain active in `.github/workflows/`:

- `submission.yml` — automatic unit, integrity, preflight, and benchmark smoke checks on PRs/pushes to `main`;
- `phase9.yml` — manual reproduction of the final primary regression and held-out agent trajectory.

Historical experiment results remain in the repository; obsolete workflow definitions are removed from the active Actions menu to avoid accidental expensive reruns.
