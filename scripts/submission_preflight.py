#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "REPRODUCE.md",
    "IMPROVEMENT_CHANGELOG.md",
    "SUBMISSION.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "Makefile",
    "requirements.txt",
    "docs/PROBLEM.md",
    "docs/EVALUATION.md",
    "docs/PHASE_4_RESULT.md",
    "docs/PHASE_5.md",
    "docs/PHASE_8.md",
    "docs/COMPETITION_PROVENANCE.md",
    "docs/RULEBOOK_COMPLIANCE.md",
    "docs/AGENT_TRAJECTORIES.md",
    "docs/REPOSITORY_MAP.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "docs/VIDEO_PLAN.md",
    "benchmark/cases.json",
    "benchmark/oracles.py",
    "benchmark/reference_repairs.py",
    "benchmark/public_context.py",
    "driftdoctor/repair_skills.py",
    "driftdoctor/contract_checks.py",
    "driftdoctor/ambiguity.py",
    "driftdoctor/v4.py",
    "scripts/validate_benchmark.py",
    "scripts/smoke_benchmark.py",
    "scripts/run_phase5.py",
    "scripts/run_phase8.py",
    "scripts/run_phase9_primary.py",
    "scripts/run_agent_fallback_demo.py",
    "scripts/run_incident.py",
    "tests/test_run_incident_safety.py",
    "tests/test_repair_skills.py",
    "tests/test_repair_skill_mutations.py",
    "tests/test_contract_checks.py",
    "tests/test_ambiguity.py",
    "tests/test_final_runtime_integrity.py",
    "evidence/phase5/README.md",
    "evidence/phase5/manifest.json",
    "evidence/phase5/context-baseline/summary.json",
    "evidence/phase5/driftdoctor-no-review/summary.json",
    "evidence/phase5/driftdoctor-review-incomplete/summary.json",
    "evidence/phase8/README.md",
    "evidence/phase8/manifest.json",
    "evidence/phase8/skills-only/summary.json",
    "evidence/phase8/hybrid/summary.json",
    "evidence/phase9/README.md",
    "evidence/phase9/manifest.json",
    "evidence/phase9/primary-summary.json",
    "evidence/phase9/agent-fallback-demo.json",
]

FINAL_RUNTIME = [
    "driftdoctor/repair_skills.py",
    "driftdoctor/contract_checks.py",
    "driftdoctor/ambiguity.py",
    "driftdoctor/v4.py",
]

ALLOWED_WORKFLOWS = {"submission.yml", "phase9.yml"}
ACTION_REF_RE = re.compile(r"uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_phase8_result(
    root: Path,
    expected_system: str,
    failures: list[str],
) -> dict | None:
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        fail(f"missing Phase 8 summary: {summary_path.relative_to(ROOT)}", failures)
        return None
    data = load_json(summary_path)
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
        fail(f"{root.name} VRR must remain 12/12", failures)
    if data.get("root_cause_correct") != 12 or data.get("root_cause_accuracy") != 1.0:
        fail(f"{root.name} root-cause result must remain 12/12", failures)
    if float(data.get("mean_model_calls", -1)) != 0.0:
        fail(f"{root.name} must preserve zero model calls", failures)
    if data.get("fallback_cases") != 0:
        fail(f"{root.name} must preserve zero fallback cases", failures)
    for path in case_files:
        case = load_json(path)
        if case.get("status") != "scored" or case.get("passed") is not True:
            fail(f"Phase 8 case is not a verified pass: {path.relative_to(ROOT)}", failures)
        if case.get("root_cause_correct") is not True:
            fail(f"Phase 8 root-cause result changed: {path.relative_to(ROOT)}", failures)
        if case.get("model_calls") != 0 or case.get("fallback_used") is not False:
            fail(f"Phase 8 case unexpectedly used a model/fallback: {path.relative_to(ROOT)}", failures)
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

    print("\nBenchmark contract audit")
    cases_path = ROOT / "benchmark" / "cases.json"
    if cases_path.is_file():
        cases = load_json(cases_path).get("cases", [])
        ids = [case.get("id") for case in cases]
        if len(cases) != 12 or len(set(ids)) != 12:
            fail(f"benchmark must contain 12 unique cases, found {len(cases)}", failures)
        challenge = [case for case in cases if case.get("challenge_case")]
        if len(challenge) != 1 or challenge[0].get("id") != "DD-012":
            fail("expected exactly one challenge case, DD-012", failures)
        if not all(case.get("incident") and case.get("root_cause_class") for case in cases):
            fail("every case must declare incident and root-cause class", failures)
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
        data = load_json(summary_path)
        if len(list(root.glob("DD-*.json"))) != 12:
            fail(f"{system} must preserve 12 raw case records", failures)
        if data.get("complete") is not True or data.get("scored_cases") != 12:
            fail(f"{system} must remain a complete 12/12 result", failures)
        if data.get("solved") != solved:
            fail(f"{system} historical solved count changed", failures)
        if abs(float(data.get("verified_resolution_rate", -1)) - vrr) > 1e-12:
            fail(f"{system} historical VRR changed", failures)
        if data.get("root_cause_correct") != roots:
            fail(f"{system} historical root-cause count changed", failures)

    review_summary = phase5 / "driftdoctor-review-incomplete" / "summary.json"
    if review_summary.is_file():
        review = load_json(review_summary)
        if review.get("complete") is not False:
            fail("removed semantic reviewer must remain explicitly incomplete", failures)
        if review.get("verified_resolution_rate") is not None:
            fail("removed semantic reviewer must remain unscored with null VRR", failures)
        if review.get("scored_cases") != 7:
            fail("removed semantic reviewer observed scored-case count changed", failures)
        if not review.get("infrastructure_errors"):
            fail("removed semantic reviewer must preserve infrastructure errors", failures)
    else:
        fail("removed semantic-review summary is missing", failures)

    print("\nCorrected Phase 8 evidence audit")
    phase8 = ROOT / "evidence" / "phase8"
    audit_phase8_result(phase8 / "skills-only", "driftdoctor-v4-skills-only", failures)
    hybrid8 = audit_phase8_result(phase8 / "hybrid", "driftdoctor-v4-hybrid", failures)
    if hybrid8 is not None and abs(float(hybrid8.get("mean_elapsed_seconds", -1)) - 6.9895) > 1e-12:
        fail("frozen Phase 8 hybrid mean elapsed changed", failures)

    phase8_manifest = phase8 / "manifest.json"
    if phase8_manifest.is_file():
        manifest = load_json(phase8_manifest)
        expected = {
            "workflow_run_id": 33257030328,
            "evaluation_head_sha": "0c6cf9b42863db4f45a94add11509988bcaa7815",
            "selected_system": "driftdoctor-v4-hybrid",
            "verified_resolution_rate": 1.0,
            "root_cause_accuracy": 1.0,
            "fallback_cases": 0,
            "mean_model_calls": 0.0,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                fail(f"Phase 8 manifest field changed: {key}", failures)
    else:
        fail("Phase 8 evidence manifest is missing", failures)

    print("\nFinal Phase 9 primary regression audit")
    phase9 = ROOT / "evidence" / "phase9"
    primary_path = phase9 / "primary-summary.json"
    if primary_path.is_file():
        primary = load_json(primary_path)
        expected_primary = {
            "system": "driftdoctor-v0.5-selective-agency",
            "context_version": "0.2",
            "complete": True,
            "expected_cases": 12,
            "scored_cases": 12,
            "solved": 12,
            "verified_resolution_rate": 1.0,
            "root_cause_correct": 12,
            "model_calls": 0,
            "agent_cases": 0,
            "escalation_cases": 0,
        }
        for key, value in expected_primary.items():
            if primary.get(key) != value:
                fail(f"Phase 9 primary field changed: {key}", failures)
        if primary.get("failures") != []:
            fail("Phase 9 primary regression contains failures", failures)
        if abs(float(primary.get("mean_elapsed_seconds", -1)) - 6.640333333333333) > 1e-12:
            fail("Phase 9 primary mean elapsed changed", failures)
    else:
        fail("Phase 9 primary summary is missing", failures)

    print("\nRepresentative bounded-agent trajectory audit")
    agent_path = phase9 / "agent-fallback-demo.json"
    if agent_path.is_file():
        agent = load_json(agent_path)
        control = agent.get("skills_only_control") or {}
        hybrid = agent.get("hybrid") or {}
        oracle = agent.get("oracle") or {}
        if agent.get("case") != "held-out-ambiguous-ref":
            fail("unexpected held-out agent case identifier", failures)
        if "not part of the frozen 12-case primary VRR" not in str(agent.get("purpose", "")):
            fail("held-out agent trajectory must remain outside primary VRR", failures)
        if int(control.get("build_returncode", 0)) == 0 or control.get("escalation_required") is not True:
            fail("skills-only held-out control must remain broken and escalated", failures)
        if control.get("model_calls") != 0:
            fail("skills-only held-out control unexpectedly used a model", failures)
        if hybrid.get("system") != "driftdoctor-v0.5-selective-agency":
            fail("held-out trajectory system changed", failures)
        if hybrid.get("model_calls") != 1:
            fail("held-out bounded agent must preserve exactly one model call", failures)
        if hybrid.get("fallback_mode") != "bounded_ambiguity_resolver":
            fail("held-out trajectory bounded mode changed", failures)
        if hybrid.get("escalation_required") is not False:
            fail("successful held-out agent result unexpectedly escalates", failures)
        trajectory = hybrid.get("trajectory") or []
        resolver = next((step for step in trajectory if step.get("stage") == "ambiguity_resolver"), None)
        if resolver is None:
            fail("held-out trajectory lacks ambiguity-resolver step", failures)
        else:
            ambiguity = resolver.get("ambiguity") or {}
            candidates = ambiguity.get("candidates") or []
            selection = (resolver.get("decision") or {}).get("selection")
            if sorted(candidates) != ["stg_orders_archive", "stg_orders_v2"]:
                fail("held-out observed candidate set changed", failures)
            if selection != "stg_orders_v2" or selection not in candidates:
                fail("held-out agent selection is not the observed active candidate", failures)
        if oracle.get("passed") is not True:
            fail("held-out agent evaluator no longer passes", failures)
        checks = oracle.get("checks") or {}
        if not checks or not all(checks.values()):
            fail("one or more held-out agent checks failed", failures)
    else:
        fail("representative bounded-agent trajectory is missing", failures)

    print("\nPhase 9 provenance audit")
    phase9_manifest_path = phase9 / "manifest.json"
    if phase9_manifest_path.is_file():
        manifest = load_json(phase9_manifest_path)
        if manifest.get("workflow_run_id") != 33259014887:
            fail("Phase 9 workflow run provenance changed", failures)
        if manifest.get("evaluation_head_sha") != "33caefca6a5a003090edea1ba6cc5d3cc0bd2dbc":
            fail("Phase 9 evaluation SHA changed", failures)
        primary_meta = manifest.get("primary_regression") or {}
        if primary_meta.get("artifact_id") != 9716719953:
            fail("Phase 9 primary artifact ID changed", failures)
        if primary_meta.get("artifact_digest") != "sha256:e41106ab0169566e8492bd0d125956f8cc9d59323aa8071c61ddcc2946753d78":
            fail("Phase 9 primary artifact digest changed", failures)
        if primary_path.is_file() and primary_meta.get("checked_in_summary_sha256") != sha256(primary_path):
            fail("Phase 9 checked-in primary summary hash does not match manifest", failures)
        agent_meta = manifest.get("representative_agent_trajectory") or {}
        if agent_meta.get("artifact_id") != 9716761142:
            fail("Phase 9 agent artifact ID changed", failures)
        if agent_meta.get("artifact_digest") != "sha256:77a7807842b16193afa23385bbc216794ec382d78e8b2c487d82f53791fc5c4a":
            fail("Phase 9 agent artifact digest changed", failures)
        if agent_meta.get("part_of_primary_vrr") is not False:
            fail("Phase 9 agent trajectory must not be marked as primary VRR", failures)
        if agent_path.is_file() and agent_meta.get("checked_in_record_sha256") != sha256(agent_path):
            fail("Phase 9 checked-in agent record hash does not match manifest", failures)
    else:
        fail("Phase 9 evidence manifest is missing", failures)

    print("\nFinal runtime anti-leakage and safety audit")
    for relative in FINAL_RUNTIME:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\bDD-\d{3}\b", text):
            fail(f"{relative} contains a benchmark case ID", failures)
        if re.search(r"(?m)^\s*(?:from|import)\s+benchmark(?:\.|\s)", text):
            fail(f"{relative} imports evaluator/benchmark runtime", failures)
        for forbidden in ("reference_repairs", "oracle_checks", "evaluate_case"):
            if forbidden in text:
                fail(f"{relative} contains evaluator-specific token: {forbidden}", failures)
    v4_text = (ROOT / "driftdoctor" / "v4.py").read_text(encoding="utf-8", errors="replace")
    if "run_v3" in v4_text or "from driftdoctor.v3" in v4_text:
        fail("final orchestrator imports historical open-ended coding fallback", failures)
    ambiguity_text = (ROOT / "driftdoctor" / "ambiguity.py").read_text(encoding="utf-8", errors="replace")
    for required in ("abstain", "enum", "Allowed candidates"):
        if required.lower() not in ambiguity_text.lower():
            fail(f"bounded ambiguity agent is missing required constraint marker: {required}", failures)
    cli_text = (ROOT / "scripts" / "run_incident.py").read_text(encoding="utf-8", errors="replace")
    for required in ("refusing non-DuckDB target", "human_approval_required", "human_escalation_required", "SANDBOX_MARKER"):
        if required not in cli_text:
            fail(f"judge CLI is missing safety requirement: {required}", failures)

    print("\nLicense, data, and competition provenance audit")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace") if (ROOT / "LICENSE").is_file() else ""
    if "MIT License" not in license_text or "2026 Aarya Mody" not in license_text:
        fail("project MIT license/copyright is incomplete", failures)
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8", errors="replace") if (ROOT / "THIRD_PARTY_NOTICES.md").is_file() else ""
    for component in ("dbt Core", "dbt-duckdb", "DuckDB", "PyYAML", "Ollama", "Qwen2.5-Coder"):
        if component not in notices:
            fail(f"third-party notice is missing {component}", failures)
    provenance = (ROOT / "docs" / "COMPETITION_PROVENANCE.md").read_text(encoding="utf-8", errors="replace") if (ROOT / "docs" / "COMPETITION_PROVENANCE.md").is_file() else ""
    if "Before the competition" not in provenance or "Added during the competition" not in provenance:
        fail("competition provenance does not distinguish before/during work", failures)
    if "synthetic" not in notices.lower() or "credentials" not in notices.lower():
        fail("third-party/data notice must document synthetic data and credential boundary", failures)

    print("\nWorkflow cleanliness and supply-chain audit")
    workflows_dir = ROOT / ".github" / "workflows"
    workflow_names = {path.name for path in workflows_dir.glob("*.yml")}
    if workflow_names != ALLOWED_WORKFLOWS:
        fail(
            f"active workflow set must be exactly {sorted(ALLOWED_WORKFLOWS)}, found {sorted(workflow_names)}",
            failures,
        )
    for workflow in sorted(workflows_dir.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = ACTION_REF_RE.search(line)
            if match and not FULL_SHA_RE.fullmatch(match.group(2)):
                fail(
                    f"{workflow.relative_to(ROOT)}:{line_number} must pin {match.group(1)} to a full SHA",
                    failures,
                )
    submission = (workflows_dir / "submission.yml").read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?m)^\s{2}pull_request:", submission) or not re.search(r"(?m)^\s{2}push:", submission):
        fail("submission workflow must validate both PRs and main pushes", failures)
    phase9_workflow = (workflows_dir / "phase9.yml").read_text(encoding="utf-8", errors="replace")
    if "workflow_dispatch:" not in phase9_workflow:
        fail("Phase 9 evidence workflow must be manually dispatchable", failures)
    if re.search(r"(?m)^\s{2}(push|pull_request):", phase9_workflow):
        fail("Phase 9 model/evaluation workflow must remain manual-only", failures)

    print("\nRulebook deliverable and claim-hygiene audit")
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    required_readme = [
        "analytics and data engineers",
        "12/12",
        "100% VRR",
        "0 model calls",
        "bounded ambiguity agent",
        "held-out",
        "human escalation",
        "not a claim",
        "A green pipeline is not a verified pipeline",
        "knowing when not to call the model",
    ]
    for phrase in required_readme:
        if phrase.lower() not in readme.lower():
            fail(f"README missing required final claim/scope element: {phrase!r}", failures)
    forbidden_claims = [
        "production-ready",
        "guarantees every repair",
        "solves arbitrary dbt",
        "measurement in progress",
        "final winner/VRR claims remain gated",
    ]
    for phrase in forbidden_claims:
        if phrase.lower() in readme.lower():
            fail(f"README contains stale/unsupported claim: {phrase!r}", failures)
    if "separate" not in readme.lower() or "not" not in readme.lower().split("held-out", 1)[-1][:400]:
        fail("README must clearly keep held-out agent evidence separate from primary VRR", failures)

    rulebook = (ROOT / "docs" / "RULEBOOK_COMPLIANCE.md").read_text(encoding="utf-8", errors="replace")
    for heading in (
        "Four required questions",
        "Judging rubric",
        "Ground rules",
        "Final deliverables",
        "Remaining manual-only steps",
    ):
        if heading not in rulebook:
            fail(f"rulebook compliance document missing section: {heading}", failures)

    trajectories = (ROOT / "docs" / "AGENT_TRAJECTORIES.md").read_text(encoding="utf-8", errors="replace")
    for required in (
        "Frozen simple-agent baseline",
        "Schema-constrained staged repair agent",
        "Semantic-review agent",
        "Final bounded ambiguity-resolver agent",
        "Human checkpoints",
    ):
        if required not in trajectories:
            fail(f"agent trajectory index missing agent/checkpoint: {required}", failures)

    reproduce = (ROOT / "REPRODUCE.md").read_text(encoding="utf-8", errors="replace")
    for required in (
        "run_phase9_primary.py",
        "run_agent_fallback_demo.py",
        "Expected output",
        "Runtime and cost",
        "Ollama 0.33.2",
    ):
        if required.lower() not in reproduce.lower():
            fail(f"reproduction guide missing required detail: {required}", failures)

    video = (ROOT / "docs" / "VIDEO_PLAN.md").read_text(encoding="utf-8", errors="replace")
    for required in (
        "Realistic end-to-end agent execution",
        "Final comparison",
        "removed experiment",
        "Reproducibility",
        "4:55",
    ):
        if required.lower() not in video.lower():
            fail(f"video plan missing required rulebook element: {required}", failures)

    submission_text = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8", errors="replace")
    if "[PASTE FINAL PASSING MAIN SHA]" not in submission_text or "[PASTE <=5 MINUTE VIDEO URL]" not in submission_text:
        fail("submission package must retain explicit manual portal placeholders", failures)

    if failures:
        print(f"\nSubmission preflight failed with {len(failures)} issue(s).")
        return 1

    print(
        "\nSubmission preflight passed: rulebook deliverables, final evidence, agent trajectory, "
        "licenses, safety controls, workflow cleanliness, claims, and provenance are consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
