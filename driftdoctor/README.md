# DriftDoctor package guide

## Final runtime

- `evidence.py` — gathers normal engineer-visible dbt execution, artifact, project, and source evidence.
- `contract_checks.py` — parses explicit business contracts and reports visible unresolved concerns.
- `repair_skills.py` — conservative deterministic repair tools for supported recurring contract-drift patterns.
- `ambiguity_agent.py` — one bounded model-backed decision agent that selects an observed existing dbt model or abstains.
- `v4.py` — final selective-agency orchestrator: evidence, skills, bounded agent, executable feedback, stopping, and human escalation.

The judge-facing entry point is `scripts/run_incident.py`.

## Historical experiment modules

- `agent.py` — first evidence-first agent workflow used in the Phase 4 experiment.
- `v2.py` — staged structured diagnosis/patch workflow used in Phase 5 and shared local inference/build utilities.
- `v3.py` — contract-guided model prototype retained for the Improvement Changelog and historical reproduction.

Historical modules remain intentionally because the challenge requires meaningful iterations—including failed and removed techniques—to be reproducible. They are not the default product path.

## Trust boundary

Runtime modules do not import benchmark case IDs, evaluator oracle code, or reference repairs. The evaluator under `benchmark/` runs only after a workflow finishes. Tests and submission preflight enforce this separation.
