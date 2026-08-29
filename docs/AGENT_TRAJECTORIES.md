# Agent trajectory index

The rulebook asks for representative trajectories for every agent used, from instructions through tool/model responses, feedback, retries, and human checkpoints. DriftDoctor preserves **observable execution records only**—prompts, structured outputs, tool results, patches, diffs, and evaluator outcomes. It does not claim or expose private model chain-of-thought.

## 1. Frozen simple-agent baseline

**Purpose:** reasonable basic comparison before DriftDoctor.

**Instructions:** [`../baseline/PROMPT.md`](../baseline/PROMPT.md)

**Capabilities:** list/read/write project files and run bounded local commands. No specialized context collector, semantic verifier, or repair skills.

**Representative trajectory:** [`../evidence/phase5/context-baseline/DD-004.json`](../evidence/phase5/context-baseline/DD-004.json)

**What to inspect:**

- incident presented to the baseline;
- tool actions and responses;
- files changed and final diff;
- external oracle result;
- failure to produce a verified repair in the matched-context run.

## 2. DriftDoctor v0.1 repair/investigation agent

**Purpose:** test whether evidence collection, dbt artifacts, and a repair/retry loop improve a small coding model.

**Instructions/runtime:** [`../driftdoctor/agent.py`](../driftdoctor/agent.py), historical Phase 4 description in [`PHASE_4.md`](PHASE_4.md).

**Representative result:** [`PHASE_4_RESULT.md`](PHASE_4_RESULT.md)

**What it revealed:** malformed action turns dropped substantially, but VRR stayed 0/12. Better protocol compliance did not automatically improve task success.

## 3. Schema-constrained staged repair agent

**Purpose:** separate diagnosis from patch generation and feed concrete dbt failures into a bounded retry.

**Instructions/runtime:** historical [`../driftdoctor/v2.py`](../driftdoctor/v2.py).

**Representative verified success:** [`../evidence/phase5/driftdoctor-no-review/DD-004.json`](../evidence/phase5/driftdoctor-no-review/DD-004.json)

**Representative failures:**

- [`../evidence/phase5/driftdoctor-no-review/DD-001.json`](../evidence/phase5/driftdoctor-no-review/DD-001.json) — diagnosis recognized the source problem but the patch repeated the broken field;
- [`../evidence/phase5/driftdoctor-no-review/DD-003.json`](../evidence/phase5/driftdoctor-no-review/DD-003.json) — technically invalid/narrow numeric repair;
- [`../evidence/phase5/driftdoctor-no-review/DD-005.json`](../evidence/phase5/driftdoctor-no-review/DD-005.json) — patch did not correctly restore the intended grain.

**Feedback/retries:** each case record contains structured diagnosis, patch output, guarded application result, dbt build feedback, retry output when used, final diff, and external oracle checks.

## 4. Semantic-review agent (removed experiment)

**Purpose:** adversarially review a green build against the visible business contract and request one targeted retry.

**Instructions/runtime:** historical review schema and prompts in [`../driftdoctor/v2.py`](../driftdoctor/v2.py).

**Evidence:** [`../evidence/phase5/driftdoctor-review-incomplete/`](../evidence/phase5/driftdoctor-review-incomplete/)

**Outcome:** the final recovery produced only 7/12 scored cases and infrastructure errors; its summary deliberately has `verified_resolution_rate=null`. The reviewer was removed rather than credited with a partial score.

## 5. Final bounded ambiguity-resolver agent

**Purpose:** make one decision that deterministic rules cannot safely make: choose among multiple **observed existing** dbt dependency candidates, or abstain.

**Instructions/runtime:** [`../driftdoctor/ambiguity.py`](../driftdoctor/ambiguity.py)

**Control and trajectory:** [`../evidence/phase9/agent-fallback-demo.json`](../evidence/phase9/agent-fallback-demo.json)

**Observable sequence:**

1. `dbt build` fails because `ref('stg_orders')` no longer exists.
2. Deterministic skills inspect the project but abstain because both `stg_orders_v2` and `stg_orders_archive` are structurally plausible.
3. The skills-only control remains broken and marks human escalation required.
4. The bounded agent receives the incident, documented business context, downstream SQL, and only those observed candidate files.
5. Its JSON schema permits `stg_orders_v2`, `stg_orders_archive`, or `abstain`; it cannot invent a name.
6. The agent selects `stg_orders_v2` and cites the visible active-vs-historical contract.
7. A deterministic patch updates only the existing downstream file.
8. `dbt build`, visible contract checks, and the held-out evaluator all pass.
9. The workflow still requires human approval before applying anything to the original project.

**Measured record:** one model call, `fallback_mode=bounded_ambiguity_resolver`, verified pass, no post-agent escalation. This held-out trajectory is kept separate from the 12-case primary VRR.

## Human checkpoints

All production-like paths stop at an approval-ready report:

- the source project is never modified;
- no remote push, merge, deployment, or warehouse mutation occurs;
- unsupported or unresolved cases set `human_escalation_required=true`;
- successful local verification still sets `human_approval_required=true`.

The CLI implementation and safety tests are in [`../scripts/run_incident.py`](../scripts/run_incident.py) and [`../tests/test_run_incident_safety.py`](../tests/test_run_incident_safety.py).
