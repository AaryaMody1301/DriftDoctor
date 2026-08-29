#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

CASE_IDS = [f"DD-{i:03d}" for i in range(1, 13)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate independently executed Phase 5 case records.")
    parser.add_argument("--system", required=True)
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.input_root)
    output = Path(args.output)
    records: dict[str, dict] = {}

    for path in sorted(root.rglob("DD-*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if record.get("system") != args.system:
            continue
        case_id = record.get("case_id")
        if case_id not in CASE_IDS:
            continue
        if case_id in records:
            raise SystemExit(f"duplicate case record for {case_id}: {path}")
        records[case_id] = record

    missing = [case_id for case_id in CASE_IDS if case_id not in records]
    infrastructure_errors = []
    summary_rows = []

    for case_id in CASE_IDS:
        record = records.get(case_id)
        if not record:
            continue
        if record.get("status") == "infrastructure_error":
            infrastructure_errors.append({
                "case_id": case_id,
                "error_type": record.get("error_type"),
                "error": record.get("error"),
            })
            continue
        if record.get("status") != "scored":
            infrastructure_errors.append({
                "case_id": case_id,
                "error_type": "InvalidCaseRecord",
                "error": f"unexpected status {record.get('status')!r}",
            })
            continue
        summary_rows.append({
            "case_id": case_id,
            "passed": bool(record.get("passed")),
            "root_cause_correct": bool(record.get("root_cause_correct")),
            "elapsed_seconds": float(record.get("elapsed_seconds", 0.0)),
            "model_calls": int(record.get("model_calls", 0)),
        })

    if missing:
        infrastructure_errors.extend(
            {"case_id": case_id, "error_type": "MissingCaseRecord", "error": "case artifact missing"}
            for case_id in missing
        )

    scored = len(summary_rows)
    solved = sum(row["passed"] for row in summary_rows)
    roots = sum(row["root_cause_correct"] for row in summary_rows)
    complete = scored == len(CASE_IDS) and not infrastructure_errors
    model = next((records[c].get("model") for c in CASE_IDS if c in records), None)

    aggregate = {
        "system": args.system,
        "context_version": "0.2",
        "model": model,
        "expected_cases": len(CASE_IDS),
        "scored_cases": scored,
        "complete": complete,
        "infrastructure_errors": infrastructure_errors,
        "solved": solved,
        "verified_resolution_rate": (solved / scored) if complete and scored else None,
        "root_cause_correct": roots,
        "root_cause_accuracy": (roots / scored) if complete and scored else None,
        "mean_elapsed_seconds": (
            sum(row["elapsed_seconds"] for row in summary_rows) / scored if scored else None
        ),
        "mean_model_calls": (
            sum(row["model_calls"] for row in summary_rows) / scored if scored else None
        ),
        "case_results": summary_rows,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(aggregate, indent=2, sort_keys=True))

    if not complete:
        raise SystemExit("Phase 5 distributed aggregate is incomplete; no VRR is publishable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
