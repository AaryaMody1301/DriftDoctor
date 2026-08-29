# Hackathon Alignment

This project structure is organized around the scoring rubric in the micro1 Agentic Workflows Hackathon brief.

| Criterion | Points | DriftDoctor evidence plan |
|---|---:|---|
| Problem & User Value | 15 | `docs/PROBLEM.md` defines the analytics/data engineer, incident bottleneck, and practical value. |
| Agent Solution & Engineering | 30 | Later phases will implement purposeful evidence gathering, repair tooling, deterministic verification, controlled retries, and explicit human approval boundaries. |
| End to End Quality | 20 | A scored run must go from incident statement to verified patch plus an approval-ready evidence report. |
| Measured Improvement | 15 | `docs/EVALUATION.md` freezes the baseline, 12 cases, VRR metric, and fairness rules before implementation. `IMPROVEMENT_CHANGELOG.md` links iterations to measured evidence. |
| Reproducibility | 15 | Synthetic data, local DuckDB, exact commands, raw result records, and a clean-environment runner will be maintained in-repo. |
| Hot Take / Insights | 5 | The working hypothesis is that evidence selection and deterministic verification matter more than simply adding agents. It will only be promoted to a conclusion if experiments support it. |

## Submission deliverable mapping

The brief asks for four final items. DriftDoctor will keep each one reproducible from the repository:

1. **Complete solution code + improvement changelog** — source plus `IMPROVEMENT_CHANGELOG.md`.
2. **Reproduction guide** — final README/runbook with exact baseline, solution, and evaluation commands; versions; runtime; and cost.
3. **Solution video (up to 5 minutes)** — script/storyboard will show the problem, baseline, one end-to-end run, measured comparison, changelog, highest-impact change, and one removed experiment.
4. **Agent trajectories** — raw representative traces will preserve instructions, tool calls/responses, verifier feedback, retries, and human checkpoints.

## Guardrails inherited from the brief

- use only licensed/allowed tools and components;
- clearly distinguish pre-existing work from hackathon work;
- use synthetic/public/approved data;
- keep credentials and private data out of the repository;
- keep consequential actions sandboxed and require human approval;
- connect every performance claim to submitted evidence;
- provide enough access and instructions for judges to reproduce the main result.
