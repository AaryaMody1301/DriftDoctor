# Phase 3 - Baseline Measurement

Phase 3 measures the frozen simple-agent baseline against the exact 12-case benchmark created in Phases 1-2.

## Why an open local model

The hackathon project has a zero-budget constraint. The baseline therefore uses `qwen2.5-coder:1.5b` through Ollama inside GitHub Actions. No paid API key is required. The same model must be used later for the direct DriftDoctor comparison unless a new comparison cohort is explicitly reported.

## Baseline workflow

For every case:

1. materialize a fresh broken project;
2. initialize a local git snapshot;
3. give the agent only the frozen incident statement and project workspace;
4. allow basic list/read/write/shell tools;
5. cap the agent at 14 model turns;
6. retain every model response and tool observation;
7. stop when the agent declares completion or reaches the turn cap;
8. run the external Phase 2 oracle outside the agent;
9. save the final diff, root-cause prediction, oracle output, elapsed time, and trajectory.

The baseline does not receive lineage-aware context selection, specialized evidence tools, external verifier feedback during the run, memory, or multi-agent orchestration.

## Isolation

File operations are path-confined to the materialized project. Shell commands reject network access, parent-directory traversal, and known hidden benchmark paths. The agent receives neither `root_cause_class` nor oracle/reference-repair implementation.

## Primary result

The primary result remains Verified Resolution Rate (VRR):

```text
verified cases / 12
```

Secondary measurements include root-cause accuracy, elapsed time, steps/tool interactions, and final patch evidence.

## Reproduce

Prerequisites:

- Python 3.13
- dbt/DuckDB dependencies from `requirements.txt`
- Ollama
- `qwen2.5-coder:1.5b`

Run:

```bash
ollama pull qwen2.5-coder:1.5b
python scripts/run_baseline.py --model qwen2.5-coder:1.5b
python scripts/summarize_baseline.py benchmark/results/baseline
```

GitHub Actions performs the same sequence and uploads the complete result directory as an artifact.

## Claim policy

Do not publish a baseline VRR until all 12 case-level result JSON files exist. No failed case may be removed from the aggregate. A rerun must be labeled as a separate run rather than replacing an inconvenient outcome silently.
