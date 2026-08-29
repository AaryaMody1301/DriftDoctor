# Phase 2 - Executable Synthetic Benchmark

Phase 2 converts the frozen evaluation contract into executable evidence.

## Exit criteria

- [x] all 12 incidents materialize as independent dbt + DuckDB workspaces;
- [x] raw inputs are synthetic and loaded locally with no warehouse credentials;
- [x] the evaluator runs outside the agent workspace;
- [x] every case has deterministic dbt/SQL/file checks;
- [x] DD-010 and DD-011 demonstrate that a green dbt build alone can still be semantically wrong;
- [x] DD-012 requires fixing two independent upstream faults;
- [x] evaluator-only reference repairs exist only to prove benchmark solvability;
- [x] CI verifies every broken fixture fails and every reference-repaired fixture passes;
- [x] runtime dependencies are pinned.

## Why materialize instead of committing 12 copied dbt trees?

A fixture factory keeps the benchmark deterministic while avoiding duplicated project boilerplate. Every scored run is still given a concrete standalone dbt project. The materialized directory can be copied, reset, diffed, and sandboxed independently.

## Safety boundary

Case materialization performs only local filesystem writes and creates a local DuckDB file. It does not require a network connection, cloud account, private data, or deployment credentials. Scored agents should be launched with the materialized directory as their only writable project surface.

## Oracle boundary

The agent is not the judge. After the agent stops, the outer harness runs `scripts/evaluate_case.py`. The result includes every check and the dbt return code. Phase 3 will add trajectory capture and baseline execution around this interface without changing the oracle.
