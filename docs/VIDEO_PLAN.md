# Five-minute submission video plan

Target length: **4:35–4:55**. Record at 1080p with terminal font large enough to read. Tell one evidence-first story; do not spend time listing technology logos or reading every file name.

## Before recording

Open these tabs/windows in order:

1. `README.md`
2. terminal in the repository virtual environment
3. `scripts/run_agent_fallback_demo.py`
4. `evidence/phase9/agent-fallback-demo.json`
5. `evidence/phase9/primary-summary.json`
6. `IMPROVEMENT_CHANGELOG.md`
7. `docs/AGENT_TRAJECTORIES.md`
8. `REPRODUCE.md`

Have Ollama 0.33.2 running and `qwen2.5-coder:1.5b` already pulled so installation/download time is not part of the recording.

## 0:00–0:30 — Problem and user

Show the README title and say:

> Analytics and data engineers often see a failure far downstream from an upstream schema, dependency, grain, or business-rule change. The difficult part is not producing any patch; it is selecting the smallest safe repair and proving the data contract still holds.

Then state:

> DriftDoctor runs locally on a disposable DuckDB-backed dbt project, produces an approval-ready diff, and never deploys or edits the original project.

Use the first insight immediately: **a green pipeline is not a verified pipeline.**

## 0:30–0:58 — Baseline and metric

Show `benchmark/cases.json` or the README result table:

- 12 frozen synthetic incidents;
- one multi-fault challenge case, DD-012;
- same context-v0.2 cases for baseline and final workflow;
- primary metric: **Verified Resolution Rate (VRR)**;
- a case counts only when every external evaluator check passes;
- matched-context simple-agent baseline: **0/12**.

Mention that evaluator-only reference repairs prove every primary case is solvable and are never available to the runtime.

## 0:58–2:22 — Realistic end-to-end agent execution

Use the held-out ambiguous dependency case because it shows why the final product still contains an agent.

Run:

```bash
python scripts/run_agent_fallback_demo.py --model qwen2.5-coder:1.5b
```

Narrate the observable steps while showing `evidence/phase9/agent-fallback-demo.json`:

1. `dbt build` fails because `mart_orders` references removed model `stg_orders`.
2. The repository contains two observed candidates: `stg_orders_v2` and `stg_orders_archive`.
3. Deterministic skills correctly **abstain**; the skills-only control remains broken and requests human escalation.
4. The bounded agent receives the incident, business context, downstream SQL, and candidate files.
5. Its structured output schema allows only the two observed candidates or `abstain`; it cannot invent a dependency or rewrite arbitrary files.
6. The agent uses one local model call and selects `stg_orders_v2` because the visible contract marks it active and marks the archive historical.
7. A deterministic existing-file patch updates `mart_orders.sql`.
8. dbt build and all held-out evaluator checks pass.
9. The result still stops at human approval.

Show the command summary:

```text
skills_only_build_returncode: 2
skills_only_escalated: true
hybrid_model_calls: 1
fallback_mode: bounded_ambiguity_resolver
hybrid_passed: true
```

Say explicitly: **this held-out trajectory is separate from the 12-case primary VRR.**

## 2:22–2:52 — Primary challenge case

Open `evidence/phase8/hybrid/DD-012.json` and show the diff:

```sql
client_name as customer_name,
try_cast(revenue_text as decimal(18,2)) as revenue_amount
```

Explain that DD-012 contains two independent faults: a renamed source field and a text/numeric change. The router selects `source_alias` and `safe_numeric`; all external checks pass. This primary case uses zero model calls because the visible contract fully determines the safe repair.

## 2:52–3:28 — Final comparison

Show this table:

| System | VRR | Root-cause accuracy | Model calls/turns | Mean time |
|---|---:|---:|---:|---:|
| matched-context simple-agent baseline | **0/12** | 0/12 | 11.75 | 39.15s/case |
| staged LLM workflow | **1/12** | 3/12 | 2.58 | 185.21s/case |
| **final selective-agency primary rerun** | **12/12** | **12/12** | **0.0** | **6.64s/case** |

State the scope precisely:

- primary improvement: **0/12 → 12/12 VRR (+100 percentage points)** on the declared benchmark;
- all 12 primary cases are contract-determined, so the agent is not artificially invoked;
- the separate held-out case demonstrates one purposeful bounded agent decision;
- neither result proves arbitrary open-ended dbt repair.

## 3:28–4:05 — Improvement changelog and removed experiment

Show `IMPROVEMENT_CHANGELOG.md` and summarize:

1. simple agent: 0/12;
2. evidence/retry workflow: better protocol compliance, still 0/12 and slower;
3. visible-context audit and fair context-v0.2 rerun;
4. staged LLM workflow: first verified repair, but only 1/12;
5. semantic-review model stage: incomplete/unscored and removed;
6. failure analysis: the small model often diagnosed correctly but patched incorrectly;
7. deterministic skills: 12/12;
8. mutation test caught a fuzzy-alias bug after the first perfect run; the test was kept, the bug fixed generically, and the whole benchmark rerun;
9. final selective agency: remove open-ended coding authority, add one constrained ambiguity decision, otherwise escalate.

The required removed experiment is the semantic-review stage. Do not claim its true VRR; its preserved aggregate is null because the run was incomplete.

## 4:05–4:34 — Reproducibility, trajectories, and safety

Show:

```bash
make verify
```

Then point to:

- `REPRODUCE.md` for clean setup, exact commands, versions, expected output, runtime, and cost;
- `docs/AGENT_TRAJECTORIES.md` for every agent used;
- `evidence/phase8/` and `evidence/phase9/` for raw records and provenance;
- `docs/RULEBOOK_COMPLIANCE.md` for the rule-by-rule audit.

Mention:

- synthetic local data;
- no warehouse credential or paid API key;
- Python/dbt/DuckDB/PyYAML versions pinned;
- Ollama/model identity pinned for the held-out agent rerun;
- action dependencies pinned to immutable SHAs;
- original project unchanged, DuckDB-only guard, no automatic deployment, human approval required.

## 4:34–4:55 — Biggest contribution and hot takes

Use this wording:

> DriftDoctor's biggest contribution is the routing policy: use models for a genuine bounded ambiguity, turn recurring contract-determined work into inspectable tools, verify externally, and escalate instead of improvising.

Finish with:

> **A green pipeline is not a verified pipeline.**
>
> **The best agent improvement was knowing when not to call the model.**

## Recording integrity

- Keep the final video at or below five minutes.
- Do not show private chain-of-thought; show only instructions, structured outputs, tool responses, diffs, retries, and checkpoints.
- Do not describe the held-out case as part of primary VRR.
- Do not call the system production-ready or claim arbitrary dbt repair.
- Put the final passing `main` SHA and repository URL in the video description.
