#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from driftdoctor.v4 import run_v4  # noqa: E402

INCIDENT = (
    "mart_orders stopped compiling after a dependency refactor. The project contains both current and historical "
    "staging models. Restore the intended dependency without changing the mart output contract."
)
CONTEXT = """# Business context

The public mart contract is `order_id`, `amount`.
The active current staging dependency is `stg_orders_v2`.
`stg_orders_archive` is a historical snapshot and must not be used for the live mart.
"""


def write_fixture(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    (root / "models").mkdir(parents=True)
    (root / "seeds").mkdir(parents=True)
    (root / "input").mkdir(parents=True)
    (root / "dbt_project.yml").write_text(
        """name: driftdoctor_fallback_demo
version: '1.0'
config-version: 2
profile: driftdoctor_demo
model-paths: [models]
seed-paths: [seeds]
models:
  driftdoctor_fallback_demo:
    +materialized: table
""",
        encoding="utf-8",
    )
    (root / "profiles.yml").write_text(
        """driftdoctor_demo:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: demo.duckdb
      schema: analytics
      threads: 1
""",
        encoding="utf-8",
    )
    (root / "BUSINESS_CONTEXT.md").write_text(CONTEXT, encoding="utf-8")
    raw = "order_id,amount\n1,10.0\n2,20.0\n"
    (root / "seeds" / "raw_orders.csv").write_text(raw, encoding="utf-8")
    # Input sample exists only as visible schema evidence for the repair workflow.
    (root / "input" / "raw_orders.csv").write_text(raw, encoding="utf-8")
    (root / "models" / "stg_orders_v2.sql").write_text(
        "select order_id, amount from {{ ref('raw_orders') }}\n", encoding="utf-8"
    )
    (root / "models" / "stg_orders_archive.sql").write_text(
        "select order_id, amount from {{ ref('raw_orders') }} where 1 = 0\n", encoding="utf-8"
    )
    (root / "models" / "mart_orders.sql").write_text(
        "select order_id, amount from {{ ref('stg_orders') }}\n", encoding="utf-8"
    )


def build(root: Path) -> dict:
    proc = subprocess.run(
        ["dbt", "build", "--profiles-dir", "."],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return {"returncode": proc.returncode, "stdout": proc.stdout[-6000:], "stderr": proc.stderr[-6000:]}


def oracle(root: Path, result: dict) -> dict:
    mart = (root / "models" / "mart_orders.sql").read_text(encoding="utf-8", errors="replace")
    final_build = build(root)
    checks = {
        "dbt_build_succeeds": final_build["returncode"] == 0,
        "current_dependency_selected": "ref('stg_orders_v2')" in mart,
        "historical_dependency_rejected": "stg_orders_archive" not in mart,
        "agent_was_used": int(result.get("model_calls", 0)) == 1,
        "bounded_resolver_used": result.get("fallback_mode") == "bounded_ambiguity_resolver",
        "no_human_escalation": result.get("escalation_required") is False,
        "no_remaining_contract_concerns": not result.get("remaining_contract_concerns"),
    }
    return {"passed": all(checks.values()), "checks": checks, "final_build": final_build}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a held-out ambiguity case that requires the bounded agent resolver.")
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--output", default="benchmark/results/phase9/agent-fallback-demo.json")
    args = parser.parse_args()

    work = ROOT / ".work" / "phase9-agent-fallback"
    skills_work = ROOT / ".work" / "phase9-skills-control"
    write_fixture(skills_work)
    skills_result = run_v4(skills_work, INCIDENT, args.model, allow_fallback=False)
    skills_oracle = build(skills_work)

    write_fixture(work)
    result = run_v4(work, INCIDENT, args.model, allow_fallback=True)
    evaluation = oracle(work, result)

    record = {
        "case": "held-out-ambiguous-ref",
        "purpose": "Representative trajectory for the final bounded ambiguity-resolver agent; not part of the frozen 12-case primary VRR.",
        "incident": INCIDENT,
        "business_context": CONTEXT,
        "skills_only_control": {
            "model_calls": skills_result.get("model_calls"),
            "fallback_used": skills_result.get("fallback_used"),
            "escalation_required": skills_result.get("escalation_required"),
            "build_returncode": skills_oracle["returncode"],
            "trajectory": skills_result,
        },
        "hybrid": result,
        "oracle": evaluation,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "skills_only_build_returncode": skills_oracle["returncode"],
        "skills_only_escalated": skills_result.get("escalation_required"),
        "hybrid_passed": evaluation["passed"],
        "hybrid_model_calls": result.get("model_calls"),
        "fallback_mode": result.get("fallback_mode"),
        "output": str(output.relative_to(ROOT)),
    }, indent=2, sort_keys=True))
    return 0 if evaluation["passed"] and skills_oracle["returncode"] != 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
