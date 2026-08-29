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

from benchmark.fixture_factory import materialize_case  # noqa: E402
from benchmark.oracles import evaluate_case  # noqa: E402
from benchmark.public_context import write_public_context  # noqa: E402
from driftdoctor.v2 import InferenceTransportError  # noqa: E402
from driftdoctor.v3 import run_v3  # noqa: E402


def load_cases() -> list[dict]:
    return json.loads((ROOT / "benchmark" / "cases.json").read_text())["cases"]


def init_git(workdir: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    subprocess.run(["git", "add", "."], cwd=workdir, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=benchmark",
            "-c",
            "user.email=benchmark@local",
            "commit",
            "-qm",
            "fixture-v0.2-context",
        ],
        cwd=workdir,
        check=True,
    )


def capture_diff(workdir: Path) -> str:
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff"],
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure the Phase 7 contract-guided workflow on the frozen v0.2 benchmark.")
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--max-calls", type=int, default=14)
    parser.add_argument("--case")
    args = parser.parse_args()

    cases = load_cases()
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            raise SystemExit(f"unknown case: {args.case}")

    results_dir = ROOT / "benchmark" / "results" / "phase7" / "driftdoctor-v3"
    if results_dir.exists():
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    infrastructure_errors: list[dict] = []

    for case in cases:
        case_id = case["id"]
        workdir = ROOT / ".work" / f"phase7-driftdoctor-v3-{case_id}"
        if workdir.exists():
            shutil.rmtree(workdir)
        materialize_case(case_id, workdir, force=True)
        write_public_context(case_id, workdir)
        init_git(workdir)

        try:
            trajectory = run_v3(
                workdir,
                case["incident"],
                args.model,
                max_model_calls=args.max_calls,
            )
        except InferenceTransportError as exc:
            record = {
                "case_id": case_id,
                "system": "driftdoctor-v3",
                "context_version": "0.2",
                "model": args.model,
                "status": "infrastructure_error",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "diff": capture_diff(workdir),
            }
            (results_dir / f"{case_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True))
            infrastructure_errors.append(record)
            print(json.dumps({"case_id": case_id, "status": "infrastructure_error", "error": str(exc)}, sort_keys=True), flush=True)
            continue

        diagnosis = trajectory.get("diagnosis") or {}
        oracle = evaluate_case(case_id, workdir, timeout_seconds=120)
        record = {
            "case_id": case_id,
            "system": "driftdoctor-v3",
            "context_version": "0.2",
            "model": args.model,
            "incident": case["incident"],
            "status": "scored",
            "passed": oracle.passed,
            "root_cause_prediction": diagnosis.get("root_cause_class"),
            "root_cause_correct": diagnosis.get("root_cause_class") == case["root_cause_class"],
            "elapsed_seconds": float(trajectory["elapsed_seconds"]),
            "model_calls": int(trajectory["model_calls"]),
            "remaining_contract_concerns": trajectory.get("remaining_contract_concerns", []),
            "oracle": oracle.to_dict(),
            "trajectory": trajectory,
            "diff": capture_diff(workdir),
        }
        (results_dir / f"{case_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        row = {
            key: record[key]
            for key in ["case_id", "passed", "root_cause_correct", "elapsed_seconds", "model_calls"]
        }
        summary.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    solved = sum(bool(row["passed"]) for row in summary)
    roots = sum(bool(row["root_cause_correct"]) for row in summary)
    expected = len(cases)
    scored = len(summary)
    complete = scored == expected and not infrastructure_errors
    aggregate = {
        "system": "driftdoctor-v3",
        "context_version": "0.2",
        "model": args.model,
        "expected_cases": expected,
        "scored_cases": scored,
        "complete": complete,
        "infrastructure_errors": [
            {"case_id": row["case_id"], "error_type": row["error_type"], "error": row["error"]}
            for row in infrastructure_errors
        ],
        "solved": solved,
        "verified_resolution_rate": (solved / scored) if complete and scored else None,
        "root_cause_correct": roots,
        "root_cause_accuracy": (roots / scored) if complete and scored else None,
        "mean_elapsed_seconds": (sum(row["elapsed_seconds"] for row in summary) / scored) if scored else None,
        "mean_model_calls": (sum(row["model_calls"] for row in summary) / scored) if scored else None,
        "case_results": summary,
    }
    (results_dir / "summary.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    print(json.dumps(aggregate, indent=2, sort_keys=True))

    if not complete:
        print("Phase 7 run is incomplete because of infrastructure errors; no VRR is publishable.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
