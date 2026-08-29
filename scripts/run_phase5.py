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
from driftdoctor.v2 import run_v2  # noqa: E402


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
    results_dir.mkdir(parents=True, exist_ok=True)
    summary = []

    for case in cases:
        case_id = case["id"]
        workdir = ROOT / ".work" / f"phase5-{args.system}-{case_id}"
        if workdir.exists():
            shutil.rmtree(workdir)
        materialize_case(case_id, workdir, force=True)
        write_public_context(case_id, workdir)
        init_git(workdir)

        trajectory, prediction, elapsed, calls = run_system(args.system, workdir, case, args.model, args.max_calls)
        oracle = evaluate_case(case_id, workdir, timeout_seconds=120)
        record = {
            "case_id": case_id,
            "system": args.system,
            "context_version": "0.2",
            "model": args.model,
            "incident": case["incident"],
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
    total = len(summary)
    aggregate = {
        "system": args.system,
        "context_version": "0.2",
        "model": args.model,
        "cases": total,
        "solved": solved,
        "verified_resolution_rate": solved / total if total else 0,
        "root_cause_correct": roots,
        "root_cause_accuracy": roots / total if total else 0,
        "mean_elapsed_seconds": sum(r["elapsed_seconds"] for r in summary) / total if total else 0,
        "mean_model_calls": sum(r["model_calls"] for r in summary) / total if total else 0,
        "case_results": summary,
    }
    (results_dir / "summary.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
