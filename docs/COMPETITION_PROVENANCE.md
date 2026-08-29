# Competition provenance

The hackathon rulebook asks participants to distinguish prior work from work added during the competition.

## Before the competition

- The `DriftDoctor` repository had been created for this project.
- Its starting contents were a short placeholder/starter `README.md` only.
- No benchmark fixtures, repair workflow, evaluation harness, agent implementation, evidence bundle, tests, reproduction guide, or submission material existed.

## Added during the competition

All functional project work in the current repository was produced during the hackathon window, including:

- the problem definition and user workflow;
- the 12-case dbt + DuckDB benchmark and external evaluator;
- the frozen simple-agent baseline;
- the evidence collector and successive model-based workflows;
- the visible business-context audit and context-v0.2 reruns;
- deterministic repair skills;
- the selective-agency router and bounded ambiguity resolver;
- safety guardrails, local CLI, tests, CI, and reproduction tooling;
- raw result records, artifact provenance, changelog, video plan, and submission checklist.

## Existing tools and components used

The project uses established open-source components rather than claiming them as original work: Python, dbt Core, dbt-duckdb, DuckDB, PyYAML, Ollama, Qwen2.5-Coder, and standard GitHub Actions. Their use and licenses are recorded in [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

## Evidence trail

The commit/PR history and [`../IMPROVEMENT_CHANGELOG.md`](../IMPROVEMENT_CHANGELOG.md) preserve the sequence from the empty foundation through failed and successful experiments. Historical evidence is retained under `evidence/phase5/`; corrected final benchmark evidence is under `evidence/phase8/`; the final selective-agent regression and representative agent trajectory are under `evidence/phase9/`.
