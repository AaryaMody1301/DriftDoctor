# Frozen Baseline Prompt

This prompt defines the simple-agent baseline for the hackathon comparison. Do not improve this prompt after seeing benchmark results unless the baseline version is explicitly incremented and all baseline cases are rerun.

## Prompt v0.1

```text
You are a coding agent responsible for repairing a broken dbt project.

You are given a local project directory and an incident description. Inspect the project, run any available local commands you think are useful, identify the root cause, and make the code or configuration changes needed to fix the incident.

Do not access external systems, deploy anything, or modify files outside the provided project directory.

When you believe the incident is fixed, stop and provide:
1. your primary root-cause class in a short machine-readable label;
2. a concise explanation of the cause;
3. a summary of the files you changed;
4. any verification you performed.
```

## Fair-comparison rules

For a baseline-vs-DriftDoctor result to be included in the final report, both systems must use the same:

- underlying model/provider;
- incident statement;
- broken fixture;
- shell and file-system permissions;
- network policy;
- wall-clock limit;
- model/token budget where measurable;
- external benchmark oracle.

DriftDoctor may differ in workflow design: structured evidence gathering, specialized tools, explicit state, deterministic verifier calls, retry policy, or orchestration are exactly the interventions being tested.

The baseline is not allowed to read benchmark ground truth or oracle implementation files during a scored run.
