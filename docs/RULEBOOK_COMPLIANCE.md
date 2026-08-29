# Hackathon rulebook compliance

This document maps the micro1 Agentic Workflows Hackathon requirements to concrete repository evidence. It is intentionally operational: a judge should be able to follow each link rather than accept an unsupported statement.

## Four required questions

| Rulebook question | DriftDoctor answer | Evidence |
|---|---|---|
| Who has this problem? | Analytics and data engineers responsible for dbt pipelines. | [`PROBLEM.md`](PROBLEM.md), [`../README.md`](../README.md) |
| What bottleneck makes it worth solving? | Evidence is scattered across build failures, SQL/YAML, source shape, dependencies, tests, and business rules; the difficult part is choosing a safe repair and proving it preserves the contract. | [`PROBLEM.md`](PROBLEM.md) |
| Does the agent solve it well? | Known contract-determined cases are routed to verified skills; one bounded agent handles an explicit unresolved dependency ambiguity or abstains; unsupported work escalates to a human. | [`PHASE_8.md`](PHASE_8.md), [`../evidence/phase9/README.md`](../evidence/phase9/README.md) |
| Can another person reproduce the result? | The benchmark is synthetic/local, dependencies are pinned, commands and expected outputs are documented, raw evidence and provenance are checked in. | [`../REPRODUCE.md`](../REPRODUCE.md), [`../evidence/phase8/`](../evidence/phase8/), [`../evidence/phase9/`](../evidence/phase9/) |

## Judging rubric

### Problem & User Value — 15

- Clearly defined primary user and incident workflow: [`PROBLEM.md`](PROBLEM.md).
- Concrete operational scope: dbt schema, type, dependency, grain, data-quality, and business-contract drift.
- Usable output: guarded patch, executable verification, evidence-rich JSON report, and human-approval boundary through [`../scripts/run_incident.py`](../scripts/run_incident.py).

### Agent Solution & Engineering — 30

- Purposeful routing rather than unnecessary agent count.
- Deterministic evidence and specialized skills for well-specified work: [`../driftdoctor/repair_skills.py`](../driftdoctor/repair_skills.py).
- Generic visible-contract verification: [`../driftdoctor/contract_checks.py`](../driftdoctor/contract_checks.py).
- Bounded ambiguity resolver that can select only an observed candidate or abstain: [`../driftdoctor/ambiguity.py`](../driftdoctor/ambiguity.py).
- Final orchestration, verification, stopping, and escalation policy: [`../driftdoctor/v4.py`](../driftdoctor/v4.py).
- Anti-leakage and mutation/generalization tests: [`../tests/`](../tests/).
- Representative agent trajectory: [`AGENT_TRAJECTORIES.md`](AGENT_TRAJECTORIES.md), [`../evidence/phase9/agent-fallback-demo.json`](../evidence/phase9/agent-fallback-demo.json).

### End-to-End Quality — 20

- Broken local project → evidence → skill/agent routing → guarded edit → dbt verification → approval-ready report.
- Original project is never modified; no deployment or merge occurs.
- CLI rejects non-DuckDB profiles, unsafe sandbox paths, and deletion of unowned directories.
- The challenging DD-012 case has an end-to-end verified trajectory in [`../evidence/phase8/hybrid/DD-012.json`](../evidence/phase8/hybrid/DD-012.json).
- A separate held-out ambiguity case demonstrates the bounded agent path and a skills-only control.

### Measured Improvement — 15

- One frozen primary metric: Verified Resolution Rate (VRR), defined in [`EVALUATION.md`](EVALUATION.md).
- 12 fixed cases plus one explicit multi-fault challenge case in [`../benchmark/cases.json`](../benchmark/cases.json).
- Fair matched-context comparison:
  - simple-agent baseline: 0/12;
  - staged LLM workflow: 1/12;
  - final skill-first benchmark: 12/12.
- Complete raw records/provenance: [`../evidence/phase5/`](../evidence/phase5/), [`../evidence/phase8/`](../evidence/phase8/).
- Final selective-agency no-regression result and held-out agent evidence: [`../evidence/phase9/`](../evidence/phase9/).
- Iteration decisions, failures, removed reviewer, and mutation-test correction: [`../IMPROVEMENT_CHANGELOG.md`](../IMPROVEMENT_CHANGELOG.md).

### Reproducibility — 15

- Clean-machine instructions and exact commands: [`../REPRODUCE.md`](../REPRODUCE.md).
- Pinned Python/dbt/DuckDB/PyYAML versions; pinned Ollama version for agent reruns.
- Synthetic data and local DuckDB; no external warehouse or paid API key.
- Reference repairs prove each primary case is solvable but are evaluator-only.
- GitHub Actions dependencies use immutable commit SHAs.
- Artifact IDs, source SHAs, digests, and checked-in records are preserved in evidence manifests.

### Hot Take / Insights — 5

- **A green pipeline is not a verified pipeline.** Semantic oracles catch failures that compile successfully.
- **The best agent improvement was knowing when not to call the model.** Skills handle deterministic work; a model is reserved for bounded ambiguity; unsupported cases escalate.
- **A perfect benchmark score still needs adversarial checks.** A mutation test invalidated the first 12/12 implementation, the generic bug was fixed, and the full benchmark was rerun before evidence was frozen.

## Ground rules

| Ground rule | Compliance |
|---|---|
| Make prior work vs competition work clear | [`COMPETITION_PROVENANCE.md`](COMPETITION_PROVENANCE.md) |
| Respect component licenses and terms | [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), [`../LICENSE`](../LICENSE) |
| Control consequential actions through sandbox/simulation | Disposable local workspaces; original project unchanged; DuckDB-only CLI |
| Add human approval / qualified reviewer | Every CLI report sets `human_approval_required=true`; unsupported ambiguity escalates instead of autonomous editing |
| Legal and ethical use | Local software-repair workflow; no people scoring, surveillance, or private data |
| Use shareable data | Benchmark is entirely synthetic |
| Keep credentials/private information out | No secrets required; project-local DuckDB profile only |
| Connect claims to evidence | Quantitative claims point to checked-in raw records and manifests |
| Give judges enough access | Public repository, pinned setup, exact commands, expected outputs, no paid key |

## Final deliverables

### 1. Complete solution code and Improvement Changelog

- Runtime: [`../driftdoctor/`](../driftdoctor/)
- Benchmark/evaluator: [`../benchmark/`](../benchmark/)
- CLI and scripts: [`../scripts/`](../scripts/)
- Tests: [`../tests/`](../tests/)
- Changelog: [`../IMPROVEMENT_CHANGELOG.md`](../IMPROVEMENT_CHANGELOG.md)
- Agent instructions are embedded in the frozen baseline prompt and bounded agent runtime; their locations are indexed in [`AGENT_TRAJECTORIES.md`](AGENT_TRAJECTORIES.md).

### 2. Reproduction guide

- [`../REPRODUCE.md`](../REPRODUCE.md) includes setup, primary/final/historical commands, expected outputs, versions, runtime, and zero API cost.

### 3. Solution video (maximum five minutes)

- Recording plan: [`VIDEO_PLAN.md`](VIDEO_PLAN.md).
- The repository cannot record or upload the human-presented video; that is a portal-time manual step.

### 4. Agent trajectories

- Index and explanation: [`AGENT_TRAJECTORIES.md`](AGENT_TRAJECTORIES.md).
- Durable representative final agent record: [`../evidence/phase9/agent-fallback-demo.json`](../evidence/phase9/agent-fallback-demo.json).
- Historical baseline, staged agent, and removed reviewer records are preserved under [`../evidence/phase5/`](../evidence/phase5/).

## Remaining manual-only steps

1. Record the ≤5-minute video from [`VIDEO_PLAN.md`](VIDEO_PLAN.md).
2. Upload the video to the allowed host.
3. Enter the final passing `main` commit SHA, repository URL, video URL, and submission text from [`../SUBMISSION.md`](../SUBMISSION.md) into HackerEarth.
