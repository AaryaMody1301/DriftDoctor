# Problem Definition

## Intended user

DriftDoctor is for analytics engineers and data engineers who own dbt transformations and must restore a pipeline after an upstream schema, contract, or business-logic change.

The benchmark assumes a small-to-medium dbt project that can be reproduced locally with DuckDB. This keeps evaluation deterministic, inexpensive, and safe.

## Bottleneck

A pipeline incident rarely arrives as a clean root-cause statement. The engineer may see a failing model, a failing test, or a silently wrong output while the actual cause lives upstream. They then have to connect several evidence sources:

- failing command output and test failures
- model SQL and macros
- source/model schemas
- lineage/dependencies
- recent code or fixture changes
- project artifacts such as `manifest.json` and `run_results.json`

The costly part is not generating a patch. It is deciding **which change is actually responsible**, making the **smallest safe repair**, and proving the repair does not break another invariant.

## User promise

For a supported incident, DriftDoctor should produce:

1. an evidence-backed root-cause statement;
2. the smallest reasonable code/configuration repair;
3. a regression check that would catch the incident class again when appropriate;
4. deterministic verification output;
5. an approval-ready summary that links claims to evidence.

The benchmark does not award success for diagnosis alone. The final project state must satisfy the case oracle.

## Why an agent is appropriate

The task combines open-ended investigation with deterministic tools. An agent can decide which files, lineage edges, logs, and tests are relevant, while dbt/DuckDB can verify whether the resulting repair is actually valid.

The design hypothesis for the hackathon is:

> Better evidence selection and deterministic verification will improve reliability more than simply adding more autonomous agents.

This is a hypothesis, not a result. It will only become a submission claim if the fixed benchmark supports it.

## Scope

### In scope

- dbt projects backed by a local DuckDB database
- synthetic/public benchmark data only
- schema drift
- contract/configuration drift
- dependency/ref drift
- data-quality regressions
- semantic SQL regressions that can be captured by deterministic assertions
- local code/config edits
- human approval before any external or consequential action

### Out of scope for the hackathon version

- automatic production deployment
- automatic GitHub merge
- modifying a live warehouse
- accessing private customer data
- generalized incident response for every orchestration platform
- probabilistic self-grading by the same model that generated the patch

## Safety boundary

All benchmark incidents must execute inside disposable local fixtures. The workflow may edit only the working copy for the active case. It must not push, deploy, merge, delete remote resources, or mutate production systems.

If the product later exposes an action that can affect an external system, it must require explicit human approval before execution.

## Evidence discipline

Every claimed resolution must be traceable to machine-generated evidence. At minimum, each run should retain:

- case identifier
- input incident statement
- commands executed
- relevant stdout/stderr or structured artifacts
- files inspected/changed
- patch/diff
- verification command and result
- elapsed time
- agent/model configuration when applicable

This evidence becomes both the evaluation record and the representative agent trajectory required for the final submission.
