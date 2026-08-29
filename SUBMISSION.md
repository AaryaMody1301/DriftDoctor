# DriftDoctor — submission package

Use this file when completing the HackerEarth form. Replace the bracketed video URL and final commit SHA only after the final `main` validation is green.

## Project title

**DriftDoctor — selective agents for verified dbt incident repair**

## One-line description

DriftDoctor diagnoses and repairs dbt contract drift by routing deterministic work to auditable repair skills, using one bounded local agent only for genuine dependency ambiguity, and verifying every patch in a disposable DuckDB sandbox before human approval.

## Problem and user

Analytics and data engineers often see a failing test, compiler error, or silently wrong mart far downstream from the real upstream change. They must correlate source shape, SQL/YAML, dependencies, tests, and business rules before they can make a safe repair. A plausible patch or green build is not enough; the repaired data contract must be verified and reviewable.

## Solution

DriftDoctor performs:

1. broken-state dbt execution and local evidence collection;
2. high-confidence contract-derived repair skills for recurring schema/type/dependency/grain/semantic drift;
3. guarded edits to existing project files only;
4. generic visible-contract checks plus dbt build/tests;
5. one bounded ambiguity agent when multiple observed dependency candidates remain—the agent can select an existing candidate or abstain, but cannot invent a path;
6. human escalation when no bounded verified repair is available;
7. an approval-ready JSON report and diff; no automatic deployment or source-project mutation.

## Primary measured result

On the frozen 12-case context-v0.2 synthetic dbt + DuckDB benchmark:

| System | VRR | Root-cause accuracy | Mean model calls/turns | Mean elapsed |
|---|---:|---:|---:|---:|
| matched-context simple-agent baseline | 0/12 (0%) | 0/12 | 11.75 | 39.15s/case |
| staged LLM workflow | 1/12 (8.33%) | 3/12 | 2.58 | 185.21s/case |
| final selective-agency entry point | **12/12 (100%)** | **12/12** | **0.0** | **6.64s/case** |

All 12 primary cases matched deterministic high-confidence skills, so the agent was not needed in the primary run. This result is scoped to the declared benchmark, not arbitrary dbt repair.

## Agent-specific evidence

A separate held-out ambiguous dependency case demonstrates the purposeful agent role without altering the primary metric:

- skills-only control: build failed and human escalation was required;
- bounded agent: one local Qwen2.5-Coder 1.5B call;
- allowed action: select `stg_orders_v2`, select `stg_orders_archive`, or abstain;
- result: selected the documented active model, guarded patch applied, dbt build and all held-out checks passed;
- full observable trajectory: `evidence/phase9/agent-fallback-demo.json`.

## Biggest contribution

The main improvement was not adding more autonomous stages. It was changing the routing policy: **use deterministic tools when the visible contract determines the repair; use a constrained agent only when a real ambiguity remains; escalate instead of improvising.**

## Removed experiment

An adversarial semantic-review model stage was removed. Its final recovery produced only 7/12 scored cases with infrastructure failures, so its VRR remains null. It added latency and transport exposure without complete comparable evidence.

## Hot takes

1. **A green pipeline is not a verified pipeline.**
2. **The best agent improvement was knowing when not to call the model.**

## Reproduction

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
python scripts/validate_benchmark.py
python scripts/smoke_benchmark.py --timeout 90
python scripts/run_phase9_primary.py
python scripts/submission_preflight.py
```

The primary final result requires no model runtime. Reproducing the held-out agent trajectory additionally requires Ollama 0.33.2 and `qwen2.5-coder:1.5b`; exact commands are in `REPRODUCE.md`.

## Links and final fields

- Repository: https://github.com/AaryaMody1301/DriftDoctor
- Final commit SHA: `[PASTE FINAL PASSING MAIN SHA]`
- Video: `[PASTE <=5 MINUTE VIDEO URL]`
- Reproduction guide: `REPRODUCE.md`
- Changelog: `IMPROVEMENT_CHANGELOG.md`
- Rulebook audit: `docs/RULEBOOK_COMPLIANCE.md`
- Agent trajectory index: `docs/AGENT_TRAJECTORIES.md`
- Final primary evidence: `evidence/phase8/` and `evidence/phase9/primary-summary.json`
- Representative bounded-agent trajectory: `evidence/phase9/agent-fallback-demo.json`

## Final manual checklist

- [ ] Record the video using `docs/VIDEO_PLAN.md` and keep it at or below five minutes.
- [ ] Confirm the latest `main` `submission-preflight` workflow passed.
- [ ] Replace both bracketed values above.
- [ ] Submit the public repository URL, final SHA, video URL, and project description through HackerEarth.
