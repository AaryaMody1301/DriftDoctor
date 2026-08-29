#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "REPRODUCE.md",
    "IMPROVEMENT_CHANGELOG.md",
    "requirements.txt",
    "docs/PROBLEM.md",
    "docs/EVALUATION.md",
    "docs/PHASE_4_RESULT.md",
    "docs/PHASE_5.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "docs/VIDEO_PLAN.md",
    "benchmark/cases.json",
    "benchmark/oracles.py",
    "benchmark/reference_repairs.py",
    "benchmark/public_context.py",
    "scripts/validate_benchmark.py",
    "scripts/smoke_benchmark.py",
    "scripts/run_phase5.py",
    "scripts/aggregate_phase5.py",
    "scripts/run_incident.py",
    "evidence/phase5/README.md",
    "evidence/phase5/manifest.json",
    "evidence/phase5/context-baseline/summary.json",
    "evidence/phase5/driftdoctor-no-review/summary.json",
    "evidence/phase5/driftdoctor-review-incomplete/summary.json",
]

PUBLISHABLE_SYSTEMS = ["context-baseline", "driftdoctor-no-review"]
SELECTED_SYSTEM = "driftdoctor-no-review"


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text())


def main() -> int:
    failures: list[str] = []

    print("Submission file audit")
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if path.is_file():
            print(f"OK: {relative}")
        else:
            fail(f"missing required file: {relative}", failures)

    cases_path = ROOT / "benchmark" / "cases.json"
    if cases_path.is_file():
        cases = json.loads(cases_path.read_text()).get("cases", [])
        if len(cases) != 12:
            fail(f"benchmark must contain 12 cases, found {len(cases)}", failures)
        challenge = [case for case in cases if case.get("challenge_case")]
        if len(challenge) != 1:
            fail(f"expected exactly one challenge case, found {len(challenge)}", failures)
        if not all(case.get("oracle_checks") for case in cases):
            fail("every case must declare oracle checks", failures)

    print("\nFinal Phase 5 evidence audit")
    evidence_root = ROOT / "evidence" / "phase5"
    summaries: dict[str, dict] = {}
    for system in PUBLISHABLE_SYSTEMS:
        system_root = evidence_root / system
        summary_path = system_root / "summary.json"
        if not summary_path.is_file():
            fail(f"missing final summary for {system}", failures)
            continue
        data = json.loads(summary_path.read_text())
        summaries[system] = data
        case_files = sorted(system_root.glob("DD-*.json"))
        if len(case_files) != 12:
            fail(f"{system} must preserve 12 raw case records, found {len(case_files)}", failures)
        if data.get("complete") is not True:
            fail(f"{system} result must be complete", failures)
        if data.get("expected_cases") != 12 or data.get("scored_cases") != 12:
            fail(f"{system} must score exactly 12/12 cases", failures)
        if data.get("infrastructure_errors"):
            fail(f"{system} contains infrastructure errors", failures)
        if data.get("verified_resolution_rate") is None:
            fail(f"{system} has no publishable VRR", failures)

    baseline = summaries.get("context-baseline")
    selected = summaries.get(SELECTED_SYSTEM)
    if baseline and selected:
        if baseline.get("verified_resolution_rate") != 0.0:
            fail("frozen matched-context baseline VRR must be 0.0", failures)
        if selected.get("solved") != 1:
            fail("frozen final workflow must preserve exactly the measured 1 solved case", failures)
        if abs(float(selected.get("verified_resolution_rate", -1)) - (1 / 12)) > 1e-12:
            fail("frozen final workflow VRR must equal 1/12", failures)
        if selected.get("root_cause_correct") != 3:
            fail("frozen final workflow root-cause-correct count must be 3", failures)
        if selected.get("verified_resolution_rate", 0) <= baseline.get("verified_resolution_rate", 0):
            fail("selected workflow must improve publishable VRR over matched baseline", failures)

    print("\nRemoved reviewer evidence audit")
    review_root = evidence_root / "driftdoctor-review-incomplete"
    review_summary = review_root / "summary.json"
    if review_summary.is_file():
        review = json.loads(review_summary.read_text())
        if review.get("complete") is not False:
            fail("removed reviewer result must remain explicitly incomplete", failures)
        if review.get("verified_resolution_rate") is not None:
            fail("removed reviewer result must not publish a VRR", failures)
        if review.get("scored_cases") != 7:
            fail("removed reviewer evidence should preserve the observed 7 scored cases", failures)
        if not review.get("infrastructure_errors"):
            fail("removed reviewer evidence must preserve its infrastructure errors", failures)
    else:
        fail("removed reviewer summary is missing", failures)

    print("\nEvidence provenance audit")
    manifest_path = evidence_root / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("selected_system") != SELECTED_SYSTEM:
            fail("evidence manifest selected system does not match final workflow", failures)
        matched = manifest.get("matched_context_run", {})
        if not matched.get("run_id") or not matched.get("head_sha"):
            fail("matched-context workflow provenance is incomplete", failures)
        for key in ("context_baseline_artifact", "driftdoctor_no_review_artifact"):
            artifact = matched.get(key, {})
            if not artifact.get("artifact_id") or not str(artifact.get("digest", "")).startswith("sha256:"):
                fail(f"missing artifact provenance for {key}", failures)
    else:
        fail("evidence manifest is missing", failures)

    print("\nClaim hygiene audit")
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(errors="replace") if readme_path.exists() else ""
    forbidden = [
        "100% success",
        "perfect accuracy",
        "solves all incidents",
        "measurement in progress",
        "final winner/VRR claims remain gated",
    ]
    for phrase in forbidden:
        if phrase.lower() in readme.lower():
            fail(f"README contains stale/unverified claim: {phrase!r}", failures)
    if "1/12" not in readme or "8.33%" not in readme:
        fail("README must contain the frozen final VRR", failures)
    if "unscored" not in readme.lower():
        fail("README must label the incomplete reviewer arm as unscored", failures)

    if failures:
        print(f"\nSubmission preflight failed with {len(failures)} issue(s).")
        return 1
    print("\nSubmission preflight passed: final evidence, provenance, and claims are internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
