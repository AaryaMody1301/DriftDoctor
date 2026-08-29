#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from driftdoctor.v2 import InferenceTransportError, run_v2  # noqa: E402


def _incident_text(args: argparse.Namespace) -> str:
    if args.incident:
        return args.incident.strip()
    return Path(args.incident_file).read_text(encoding="utf-8").strip()


def _copy_project(source: Path, sandbox: Path) -> None:
    ignored = shutil.ignore_patterns(".git", "target", "logs", "dbt_packages", "__pycache__", ".work")
    shutil.copytree(source, sandbox, ignore=ignored)


def _init_snapshot(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=driftdoctor",
            "-c",
            "user.email=driftdoctor@local",
            "commit",
            "-qm",
            "pre-repair snapshot",
        ],
        cwd=root,
        check=True,
    )


def _diff(root: Path) -> str:
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run DriftDoctor against a disposable copy of a local dbt project and emit "
            "an approval-ready report. The source project is never modified."
        )
    )
    parser.add_argument("--project", required=True, help="Path to the source dbt project")
    incident = parser.add_mutually_exclusive_group(required=True)
    incident.add_argument("--incident", help="Incident description")
    incident.add_argument("--incident-file", help="Text file containing the incident description")
    parser.add_argument(
        "--business-context",
        help="Optional Markdown/text file containing documented business rules to copy into BUSINESS_CONTEXT.md",
    )
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--max-calls", type=int, default=14)
    parser.add_argument(
        "--semantic-review",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable the Phase 5 semantic-review stage. Default is off until the ablation is frozen.",
    )
    parser.add_argument(
        "--sandbox",
        help="Disposable output directory. Default: .work/manual-<UTC timestamp>",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing sandbox directory")
    args = parser.parse_args()

    source = Path(args.project).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"project directory does not exist: {source}")
    if not (source / "dbt_project.yml").is_file():
        raise SystemExit("source project must contain dbt_project.yml")
    if not (source / "profiles.yml").is_file():
        raise SystemExit(
            "source project must contain a local profiles.yml so the disposable run cannot depend on hidden credentials"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sandbox = Path(args.sandbox).expanduser().resolve() if args.sandbox else (ROOT / ".work" / f"manual-{stamp}").resolve()
    if sandbox.exists():
        if not args.force:
            raise SystemExit(f"sandbox already exists: {sandbox}; pass --force to replace it")
        shutil.rmtree(sandbox)

    _copy_project(source, sandbox)
    if args.business_context:
        context_path = Path(args.business_context).expanduser().resolve()
        if not context_path.is_file():
            raise SystemExit(f"business context file does not exist: {context_path}")
        (sandbox / "BUSINESS_CONTEXT.md").write_text(
            context_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    _init_snapshot(sandbox)
    incident_text = _incident_text(args)

    try:
        result = run_v2(
            sandbox,
            incident_text,
            args.model,
            max_model_calls=args.max_calls,
            semantic_review=args.semantic_review,
        )
        infrastructure_error = None
    except InferenceTransportError as exc:
        result = None
        infrastructure_error = str(exc)

    report = {
        "report_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_project": str(source),
        "sandbox_project": str(sandbox),
        "source_project_modified": False,
        "deployment_performed": False,
        "human_approval_required": True,
        "incident": incident_text,
        "model": args.model,
        "semantic_review": args.semantic_review,
        "max_model_calls": args.max_calls,
        "infrastructure_error": infrastructure_error,
        "workflow": result,
        "diff": _diff(sandbox),
        "interpretation": (
            "A successful dbt build is evidence, not proof of semantic correctness. Review the diagnosis, "
            "diff, build output, documented business rules, and project-specific tests before applying the patch."
        ),
    }
    report_path = sandbox / "driftdoctor-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Sandbox: {sandbox}")
    print(f"Approval report: {report_path}")
    if infrastructure_error:
        print(f"Infrastructure error: {infrastructure_error}", file=sys.stderr)
        return 2

    build = (result or {}).get("final_build") or {}
    print(f"dbt build return code: {build.get('returncode')}")
    print("No source files were modified and no deployment was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
