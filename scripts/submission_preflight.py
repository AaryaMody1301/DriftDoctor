#!/usr/bin/env python3
from __future__ import annotations

import json
import re
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
    "docs/PHASE_8.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "docs/VIDEO_PLAN.md",
    "benchmark/cases.json",
    "benchmark/oracles.py",
    "benchmark/reference_repairs.py",
    "benchmark/public_context.py",
    "driftdoctor/repair_skills.py",
    "driftdoctor/v4.py",
    "scripts/validate_benchmark.py",
    "scripts/smoke_benchmark.py",
    "scripts/run_phase5.py",
    "scripts/run_phase8.py",
    "scripts/run_incident.py",
    "tests/test_run_incident_safety.py",
    "tests/test_repair_skills.py",
    "evidence/phase5/README.md",
    "evidence/phase5/manifest.json",
    "evidence/phase5/context-baseline/summary.json",
    "evidence/phase5/driftdoctor-no-review/summary.json",
    "evidence/phase5/driftdoctor-review-incomplete/summary.json",
    "evidence/phase8/README.md",
    "evidence/phase8/manifest.json",
    "evidence/phase8/skills-only/summary.json",
    "evidence/phase8/hybrid/summary.json",
]

EXPENSIVE_MANUAL_WORKFLOWS = [
    ".github/workflows/baseline.yml",
    ".github/workflows/driftdoctor.yml",
    ".github/workflows/phase5.yml",
    ".github/workflows/phase5-review-recovery.yml",
    ".github/workflows/phase7.yml",
    ".github/workflows/phase8.yml",
]
ACTION_REF_RE = re.compile(r"uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _audit_complete_result(
    root: Path,
    expected_system: str,
    failures: list[str],
    *,
    require_no_fallback: bool,
) -> dict | None:
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        fail(f"missing Phase 8 summary: {summary_path.relative_to(ROOT)}", failures)
        return None
    data = _load(summary_path)
    case_files = sorted(root.glob("DD-*.json"))
    if len(case_files) != 12:
        fail(f"{root.name} must preserve 12 raw cases, found {len(case_files)}", failures)
    if data.get("system") != expected_system:
        fail(f"{root.name} system changed", failures)
    if data.get("complete") is not True:
        fail(f"{root.name} result must be complete", failures)
    if data.get("expected_cases") != 12 or data.get("scored_cases") != 12:
        fail(f"{root.name} must score exactly 12/12 cases", failures)
    if data.get("infrastructure_errors"):
        fail(f"{root.name} contains infrastructure errors", failures)
    if data.get("solved") != 12 or data.get("verified_resolution_rate") != 1.0:
        fail(f"{root.name} VRR must remain 12/12 (1.0)", failures)
    if data.get("root_cause_correct") != 12 or data.get("root_cause_accuracy") != 1.0:
        fail(f"{root.name} root-cause accuracy must remain 12/12", failures)
    if float(data.get("mean_model_calls", -1)) != 0.0:
        fail(f"{root.name} must preserve zero model calls", failures)
    if require_no_fallback and data.get("fallback_cases") != 0:
        fail(f"{root.name} must preserve zero fallback cases", failures)
    for path in case_files:
        case = _load(path)
        if case.get("status") != "scored" or case.get("passed") is not True:
            fail(f"Phase 8 case is not a verified pass: {path}", failures)
        if case.get("root_cause_correct") is not True:
            fail(f"Phase 8 root-cause result changed: {path}", failures)
        if case.get("model_calls") != 0:
            fail(f"Phase 8 case unexpectedly used model calls: {path}", failures)
        if require_no_fallback and case.get("fallback_used") is not False:
            fail(f"Phase 8 hybrid case unexpectedly used fallback: {path}", failures)
    return data


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
        cases = _load(cases_path).get("cases", [])
        if len(cases) != 12:
            fail(f"benchmark must contain 12 cases, found {len(cases)}", failures)
        challenge = [case for case in cases if case.get("challenge_case")]
        if len(challenge) != 1 or challenge[0].get("id") != "DD-012":
            fail("expected exactly one challenge case, DD-012", failures)
        if not all(case.get("oracle_checks") for case in cases):
            fail("every case must declare oracle checks", failures)

    print("\nHistorical Phase 5 evidence audit")
    phase5 = ROOT / "evidence" / "phase5"
    historical = {
        "context-baseline": (0, 0.0, 0),
        "driftdoctor-no-review": (1, 1 / 12, 3),
    }
    for system, (solved, vrr, roots) in historical.items():
        root = phase5 / system
        summary_path = root / "summary.json"
        if not summary_path.is_file():
            fail(f"missing historical summary for {system}", failures)
            continue
        data = _load(summary_path)
        if len(list(root.glob("DD-*.json"))) != 12:
            fail(f"{system} historical evidence must preserve 12 raw cases", failures)
        if data.get("complete") is not True or data.get("scored_cases") != 12:
            fail(f"{system} historical result must remain complete 12/12", failures)
        if data.get("solved") != solved:
            fail(f"{system} historical solved count changed", failures)
        if abs(float(data.get("verified_resolution_rate", -1)) - vrr) > 1e-12:
            fail(f"{system} historical VRR changed", failures)
        if data.get("root_cause_correct") != roots:
            fail(f"{system} historical root-cause count changed", failures)

    review_summary = phase5 / "driftdoctor-review-incomplete" / "summary.json"
    if review_summary.is_file():
        review = _load(review_summary)
        if review.get("complete") is not False or review.get("verified_resolution_rate") is not None:
            fail("removed semantic-review experiment must remain incomplete/unscored", failures)
    else:
        fail("removed semantic-review summary is missing", failures)

    print("\nFinal Phase 8 evidence audit")
    phase8 = ROOT / "evidence" / "phase8"
    _audit_complete_result(
        phase8 / "skills-only",
        "driftdoctor-v4-skills-only",
        failures,
        require_no_fallback=True,
    )
    hybrid = _audit_complete_result(
        phase8 / "hybrid",
        "driftdoctor-v4-hybrid",
        failures,
        require_no_fallback=True,
    )
    if hybrid is not None and abs(float(hybrid.get("mean_elapsed_seconds", -1)) - 6.9895) > 1e-12:
        fail("final hybrid mean elapsed time changed", failures)

    manifest_path = phase8 / "manifest.json"
    if manifest_path.is_file():
        manifest = _load(manifest_path)
        expected_manifest = {
            "workflow_run_id": 33257030328,
            "evaluation_head_sha": "0c6cf9b42863db4f45a94add11509988bcaa7815",
            "selected_system": "driftdoctor-v4-hybrid",
            "expected_cases": 12,
            "scored_cases": 12,
            "verified_resolution_rate": 1.0,
            "root_cause_accuracy": 1.0,
            "fallback_cases": 0,
            "mean_model_calls": 0.0,
            "mean_elapsed_seconds": 6.9895,
        }
        for key, value in expected_manifest.items():
            if manifest.get(key) != value:
                fail(f"Phase 8 manifest field changed: {key}", failures)
        hybrid_meta = manifest.get("hybrid_final") or {}
        if hybrid_meta.get("artifact_id") != 9716167394:
            fail("final hybrid artifact ID changed", failures)
        if hybrid_meta.get("artifact_digest") != "sha256:b6788eb6ed860c339daf3c822639bfde9e759457c7ac9b7825d9a5e6da3ee030":
            fail("final hybrid artifact digest changed", failures)
        skills_meta = manifest.get("skills_only_ablation") or {}
        if skills_meta.get("artifact_id") != 9716167164:
            fail("skills-only artifact ID changed", failures)
        if skills_meta.get("artifact_digest") != "sha256:404a8d60b1134ed78072421e5710ea1c0e8f19a4d15b4779e61f9c422201c030":
            fail("skills-only artifact digest changed", failures)
    else:
        fail("Phase 8 evidence manifest is missing", failures)

    print("\nRepair-skill anti-leakage audit")
    for relative in ("driftdoctor/repair_skills.py", "driftdoctor/v4.py"):
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        forbidden = ["DD-001", "DD-012", "benchmark.oracles", "reference_repairs", "evaluate_case", "oracle_checks"]
        for token in forbidden:
            if token in text:
                fail(f"{relative} contains evaluator/case-specific token: {token}", failures)

    print("\nWorkflow supply-chain audit")
    workflows_dir = ROOT / ".github" / "workflows"
    for workflow in sorted(workflows_dir.glob("*.yml")):
        text = workflow.read_text(errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = ACTION_REF_RE.search(line)
            if not match:
                continue
            action, ref = match.groups()
            if not FULL_SHA_RE.fullmatch(ref):
                fail(
                    f"{workflow.relative_to(ROOT)}:{line_number} must pin {action} to a full 40-character commit SHA",
                    failures,
                )

    for relative in EXPENSIVE_MANUAL_WORKFLOWS:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        if "workflow_dispatch:" not in text:
            fail(f"{relative} must remain manually dispatched", failures)
        if re.search(r"(?m)^\s{2}(push|pull_request):", text):
            fail(f"{relative} must not run automatically", failures)

    submission_text = (ROOT / ".github/workflows/submission.yml").read_text(errors="replace")
    if not re.search(r"(?m)^\s{2}pull_request:", submission_text):
        fail("submission workflow must validate pull requests before merge", failures)

    print("\nClaim hygiene audit")
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(errors="replace") if readme_path.exists() else ""
    forbidden_claims = [
        "production-ready",
        "guarantees every repair",
        "measurement in progress",
        "final winner/VRR claims remain gated",
    ]
    for phrase in forbidden_claims:
        if phrase.lower() in readme.lower():
            fail(f"README contains stale/unsupported claim: {phrase!r}", failures)
    required_claim_phrases = [
        "12/12",
        "100% VRR",
        "0 model calls",
        "hybrid",
        "fallback",
        "not an open-ended claim",
        "33257030328",
        "0c6cf9b42863db4f45a94add11509988bcaa7815",
    ]
    for phrase in required_claim_phrases:
        if phrase.lower() not in readme.lower():
            fail(f"README missing final scoped claim/provenance: {phrase!r}", failures)

    if failures:
        print(f"\nSubmission preflight failed with {len(failures)} issue(s).")
        return 1
    print("\nSubmission preflight passed: final hybrid evidence, anti-leakage gates, claims, workflow pins, and benchmark invariants are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
