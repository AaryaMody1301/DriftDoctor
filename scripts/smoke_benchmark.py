#!/usr/bin/env python3
"""Prove every benchmark fixture starts broken and has a passing reference repair."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.fixture_factory import case_ids, materialize_case  # noqa: E402
from benchmark.oracles import evaluate_case  # noqa: E402
from benchmark.reference_repairs import apply_reference_repair  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=case_ids())
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    selected = [args.case] if args.case else case_ids()
    root = Path(tempfile.mkdtemp(prefix="driftdoctor-smoke-"))
    results: list[dict[str, object]] = []
    failed = False

    try:
        for case_id in selected:
            workdir = root / case_id
            materialize_case(case_id, workdir)
            broken = evaluate_case(case_id, workdir, timeout_seconds=args.timeout)
            apply_reference_repair(case_id, workdir)
            repaired = evaluate_case(case_id, workdir, timeout_seconds=args.timeout)

            row = {
                "case_id": case_id,
                "broken_oracle_passed": broken.passed,
                "reference_repair_passed": repaired.passed,
                "broken_dbt_returncode": broken.dbt_returncode,
                "repaired_dbt_returncode": repaired.dbt_returncode,
                "failed_repair_checks": [c.name for c in repaired.checks if not c.passed],
            }
            results.append(row)
            print(json.dumps(row, sort_keys=True))
            if broken.passed or not repaired.passed:
                failed = True

        print(json.dumps({"cases": len(results), "passed": not failed}, sort_keys=True))
        if args.keep:
            print(f"kept at {root}")
            root = None  # type: ignore[assignment]
        return 1 if failed else 0
    finally:
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
