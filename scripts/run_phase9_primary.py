#!/usr/bin/env python3
from __future__ import annotations

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
from driftdoctor.v4 import run_v4  # noqa: E402

MODEL = "qwen2.5-coder:1.5b"


def cases() -> list[dict]:
    return json.loads((ROOT / "benchmark" / "cases.json").read_text(encoding="utf-8"))["cases"]


def init_git(workdir: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    subprocess.run(["git", "add", "."], cwd=workdir, check=True)
    subprocess.run(
        ["git", "-c", "user.name=benchmark", "-c", "user.email=benchmark@local", "commit", "-qm", "fixture"],
        cwd=workdir,
        check=True,
    )


def source_diff(workdir: Path) -> str:
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--", ".", ":(glob,exclude)**/*.duckdb"],
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout


def main() -> int:
    out = ROOT / "benchmark" / "results" / "phase9" / "primary-regression"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    rows: list[dict] = []
    failures: list[str] = []
    for case in cases():
        case_id = case["id"]
        workdir = ROOT / ".work" / f"phase9-primary-{case_id}"
        if workdir.exists():
            shutil.rmtree(workdir)
        materialize_case(case_id, workdir, force=True)
        write_public_context(case_id, workdir)
        init_git(workdir)

        try:
            result = run_v4(workdir, case["incident"], MODEL, allow_fallback=True)
        except InferenceTransportError as exc:
            failures.append(f"{case_id}: unexpectedly reached model transport: {exc}")
            continue

        oracle = evaluate_case(case_id, workdir, timeout_seconds=120)
        diagnosis = result.get("diagnosis") or {}
        prediction = result.get("skill_root_cause_class") or diagnosis.get("root_cause_class")
        record = {
            "case_id": case_id,
            "system": "driftdoctor-v0.5-selective-agency",
            "context_version": "0.2",
            "passed": oracle.passed,
            "root_cause_prediction": prediction,
            "root_cause_correct": prediction == case["root_cause_class"],
            "model_calls": int(result.get("model_calls", 0)),
            "bounded_agent_used": bool(result.get("fallback_used")),
            "escalation_required": bool(result.get("escalation_required")),
            "remaining_contract_concerns": result.get("remaining_contract_concerns") or [],
            "skills": result.get("skills") or [],
            "elapsed_seconds": float(result.get("elapsed_seconds", 0.0)),
            "oracle": oracle.to_dict(),
            "trajectory": result,
            "diff": source_diff(workdir),
        }
        (out / f"{case_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        rows.append(record)

        if not oracle.passed:
            failures.append(f"{case_id}: external oracle failed")
        if record["model_calls"] != 0 or record["bounded_agent_used"]:
            failures.append(f"{case_id}: primary regression unexpectedly invoked the agent")
        if record["escalation_required"] or record["remaining_contract_concerns"]:
            failures.append(f"{case_id}: primary regression ended with unresolved/escalated contract state")
        if not record["root_cause_correct"]:
            failures.append(f"{case_id}: root-cause classification changed")
        print(json.dumps({k: record[k] for k in ("case_id", "passed", "root_cause_correct", "model_calls", "escalation_required")}, sort_keys=True), flush=True)

    summary = {
        "system": "driftdoctor-v0.5-selective-agency",
        "context_version": "0.2",
        "expected_cases": 12,
        "scored_cases": len(rows),
        "solved": sum(bool(row["passed"]) for row in rows),
        "verified_resolution_rate": (sum(bool(row["passed"]) for row in rows) / 12) if len(rows) == 12 else None,
        "root_cause_correct": sum(bool(row["root_cause_correct"]) for row in rows),
        "model_calls": sum(int(row["model_calls"]) for row in rows),
        "agent_cases": sum(bool(row["bounded_agent_used"]) for row in rows),
        "escalation_cases": sum(bool(row["escalation_required"]) for row in rows),
        "mean_elapsed_seconds": (sum(float(row["elapsed_seconds"]) for row in rows) / len(rows)) if rows else None,
        "failures": failures,
        "complete": len(rows) == 12 and not failures,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
