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
from driftdoctor.agent import run_driftdoctor  # noqa: E402


def load_cases() -> list[dict]:
    return json.loads((ROOT / "benchmark" / "cases.json").read_text())["cases"]


def init_git(workdir: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    subprocess.run(["git", "add", "."], cwd=workdir, check=True)
    subprocess.run(["git", "-c", "user.name=benchmark", "-c", "user.email=benchmark@local", "commit", "-qm", "fixture"], cwd=workdir, check=True)


def capture_diff(workdir: Path) -> str:
    proc = subprocess.run(["git", "diff", "--no-ext-diff"], cwd=workdir, text=True, capture_output=True, check=False)
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=workdir, text=True, capture_output=True, check=False).stdout
    extra = ""
    for name in [x for x in untracked.splitlines() if x]:
        p = workdir / name
        if p.is_file() and p.stat().st_size < 100_000:
            extra += f"\n--- /dev/null\n+++ b/{name}\n" + p.read_text(errors="replace")
    return proc.stdout + extra


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--case")
    parser.add_argument("--max-model-calls", type=int, default=14)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--results", type=Path, default=ROOT / "benchmark" / "results" / "driftdoctor")
    args = parser.parse_args()

    cases = load_cases()
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            raise SystemExit(f"unknown case: {args.case}")

    args.results.mkdir(parents=True, exist_ok=True)
    summary = []
    for case in cases:
        case_id = case["id"]
        workdir = ROOT / ".work" / f"driftdoctor-{case_id}"
        if workdir.exists():
            shutil.rmtree(workdir)
        materialize_case(case_id, workdir, force=True)
        init_git(workdir)

        trajectory = run_driftdoctor(workdir, case["incident"], args.model, max_steps=args.max_model_calls, max_retries=args.max_retries)
        oracle = evaluate_case(case_id, workdir, timeout_seconds=120)
        diff = capture_diff(workdir)
        final = trajectory.get("final") or {}
        root_cause = final.get("root_cause_class")
        root_cause_correct = root_cause == case["root_cause_class"]

        record = {
            "case_id": case_id,
            "system": "driftdoctor-v0.1",
            "model": args.model,
            "incident": case["incident"],
            "passed": oracle.passed,
            "root_cause_prediction": root_cause,
            "root_cause_correct": root_cause_correct,
            "elapsed_seconds": trajectory["elapsed_seconds"],
            "model_calls": trajectory["model_calls"],
            "retries": trajectory["retries"],
            "oracle": oracle.to_dict(),
            "trajectory": trajectory,
            "diff": diff,
        }
        (args.results / f"{case_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        row = {k: record[k] for k in ["case_id", "passed", "root_cause_correct", "elapsed_seconds", "model_calls", "retries"]}
        summary.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    solved = sum(1 for r in summary if r["passed"])
    root_correct = sum(1 for r in summary if r["root_cause_correct"])
    aggregate = {
        "system": "driftdoctor-v0.1",
        "model": args.model,
        "cases": len(summary),
        "solved": solved,
        "verified_resolution_rate": solved / len(summary) if summary else 0,
        "root_cause_accuracy": root_correct / len(summary) if summary else 0,
        "case_results": summary,
    }
    (args.results / "summary.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
