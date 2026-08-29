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

from baseline.agent import run_baseline  # noqa: E402
from benchmark.fixture_factory import materialize_case  # noqa: E402
from benchmark.oracles import evaluate_case  # noqa: E402
from benchmark.public_context import write_public_context  # noqa: E402
from driftdoctor.v2 import InferenceTransportError, run_v2  # noqa: E402


def load_cases() -> list[dict]:
    return json.loads((ROOT / "benchmark" / "cases.json").read_text())["cases"]


def init_git(workdir: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    subprocess.run(["git", "add", "."], cwd=workdir, check=True)
    subprocess.run([
        "git", "-c", "user.name=benchmark", "-c", "user.email=benchmark@local",
        "commit", "-qm", "fixture-v0.2-context",
    ], cwd=workdir, check=True)


def capture_diff(workdir: Path) -> str:
    proc = subprocess.run(["git", "diff", "--no-ext-diff"], cwd=workdir, text=True, capture_output=True, check=False)
    return proc.stdout


def run_system(system: str, workdir: Path, case: dict, model: str, max_calls: int) -> tuple[dict, str | None, float, int]:
    incident = case["incident"]
    if system == "context-baseline":
        augmented = incident + "\n\nThe project contains BUSINESS_CONTEXT.md with the documented business rules. Inspect and follow it."
        result = run_baseline(workdir, augmented, model, max_steps=max_calls)
        final = result.get("final") or {}
        return result, final.get("root_cause_class"), float(result["elapsed_seconds"]), len(result["steps"])
    if system == "driftdoctor-no-review":
        result = run_v2(workdir, incident, model, max_model_calls=max_calls, semantic_review=False)
    elif system == "driftdoctor-review":
        result = run_v2(workdir, incident, model, max_model_calls=max_calls, semantic_review=True)
    else:
        raise ValueError(system)
    diagnosis = result.get("diagnosis") or {}
    return result, diagnosis.get("root_cause_class"), float(result["elapsed_seconds"]), int(result["model_calls"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", required=True, choices=["context-baseline", "driftdoctor-no-review", "driftdoctor-review"])
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--max-calls", type=int, default=14)
    parser.add_argument("--case")
    args = parser.parse_args()

    cases = load_cases()
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            raise SystemExit(f"unknown case: {args.case}")

    results_dir = ROOT / "benchmark" / "results" / "phase5" / args.system
    if results_dir.exists():
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    infrastructure_errors: list[dict] = []

    for case in cases:
        case_id = case["id"]
        workdir = ROOT / ".work" / f"phase5-{args.system}-{case_id}"
        if workdir.exists():
            shutil.rmtree(workdir)
        materialize_case(case_id, workdir, force=True)
        write_public_context(case_id, workdir)
        init_git(workdir)

        try:
            trajectory, prediction, elapsed, calls = run_system(args.system, workdir, case, args.model, args.max_calls)
        except InferenceTransportError as exc:
            error_record = {
                "case_id": case_id,
                "system": args.system,
                "context_version": "0.2",
                "model": args.model,
                "status": "infrastructure_error",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "diff": capture_diff(workdir),
            }
            (results_dir / f"{case_id}.json").write_text(json.dumps(error_record, indent=2, sort_keys=True))
            infrastructure_errors.append(error_record)
            print(json.dumps({"case_id": case_id, "status": "infrastructure_error", "error": str(exc)}, sort_keys=True), flush=True)
            continue

        oracle = evaluate_case(case_id, workdir, timeout_seconds=120)
        record = {
            "case_id": case_id,
            "system": args.system,
            "context_version": "0.2",
            "model": args.model,
            "incident": case["incident"],
            "status": "scored",
            "passed": oracle.passed,
            "root_cause_prediction": prediction,
            "root_cause_correct": prediction == case["root_cause_class"],
            "elapsed_seconds": elapsed,
            "model_calls": calls,
            "oracle": oracle.to_dict(),
            "trajectory": trajectory,
            "diff": capture_diff(workdir),
        }
        (results_dir / f"{case_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        row = {k: record[k] for k in ["case_id", "passed", "root_cause_correct", "elapsed_seconds", "model_calls"]}
        summary.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    solved = sum(bool(r["passed"]) for r in summary)
    roots = sum(bool(r["root_cause_correct"]) for r in summary)
    expected = len(cases)
    scored = len(summary)
    complete = scored == expected and not infrastructure_errors
    aggregate = {
        "system": args.system,
        "context_version": "0.2",
        "model": args.model,
        "expected_cases": expected,
        "scored_cases": scored,
        "complete": complete,
        "infrastructure_errors": [
            {"case_id": r["case_id"], "error_type": r["error_type"], "error": r["error"]}
            for r in infrastructure_errors
        ],
        "solved": solved,
        "verified_resolution_rate": (solved / scored) if complete and scored else None,
        "root_cause_correct": roots,
        "root_cause_accuracy": (roots / scored) if complete and scored else None,
        "mean_elapsed_seconds": (sum(r["elapsed_seconds"] for r in summary) / scored) if scored else None,
        "mean_model_calls": (sum(r["model_calls"] for r in summary) / scored) if scored else None,
        "case_results": summary,
    }
    (results_dir / "summary.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    print(json.dumps(aggregate, indent=2, sort_keys=True))

    if not complete:
        print("Phase 5 run is incomplete because of infrastructure errors; no VRR is publishable.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
