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

from driftdoctor.v2 import InferenceTransportError  # noqa: E402
from driftdoctor.v4 import run_v4  # noqa: E402

SANDBOX_MARKER = ".driftdoctor-sandbox"


def _read_required_text(path_value: str, label: str) -> str:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"{label} file does not exist: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"{label} must not be empty: {path}")
    return text


def _incident_text(args: argparse.Namespace) -> str:
    if args.incident is not None:
        text = args.incident.strip()
        if not text:
            raise SystemExit("incident description must not be empty")
        return text
    return _read_required_text(args.incident_file, "incident")


def _copy_project(source: Path, sandbox: Path) -> None:
    ignored = shutil.ignore_patterns(
        ".git", "target", "logs", "dbt_packages", "__pycache__", ".work", SANDBOX_MARKER
    )
    shutil.copytree(source, sandbox, ignore=ignored)


def _validate_sandbox_target(source: Path, sandbox: Path) -> None:
    source = source.resolve()
    sandbox = sandbox.resolve()
    filesystem_root = Path(sandbox.anchor).resolve()
    protected = {ROOT.resolve(), Path.home().resolve(), filesystem_root}

    if sandbox in protected:
        raise SystemExit(f"refusing unsafe sandbox target: {sandbox}")
    if sandbox == source or sandbox in source.parents or source in sandbox.parents:
        raise SystemExit(
            "sandbox must be separate from the source project and may not contain, or be contained by, it"
        )


def _prepare_sandbox(source: Path, sandbox: Path, force: bool) -> None:
    _validate_sandbox_target(source, sandbox)
    if sandbox.exists():
        if not force:
            raise SystemExit(f"sandbox already exists: {sandbox}; pass --force to replace it")
        marker = sandbox / SANDBOX_MARKER
        if not marker.is_file():
            raise SystemExit(
                f"refusing to delete unowned directory: {sandbox}; --force only replaces a prior DriftDoctor sandbox"
            )
        shutil.rmtree(sandbox)

    _copy_project(source, sandbox)
    (sandbox / SANDBOX_MARKER).write_text(
        "Disposable DriftDoctor sandbox. Safe to replace with --force.\n", encoding="utf-8"
    )


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
        "--no-fallback",
        action="store_true",
        help="Use only deterministic contract repair skills and never invoke the local coding-model fallback.",
    )
    parser.add_argument(
        "--sandbox",
        help="Disposable output directory. Default: .work/manual-<UTC timestamp>",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing directory only when it is marked as a prior DriftDoctor sandbox",
    )
    args = parser.parse_args()

    source = Path(args.project).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"project directory does not exist: {source}")
    if not (source / "dbt_project.yml").is_file():
        raise SystemExit("source project must contain dbt_project.yml")
    if not (source / "profiles.yml").is_file():
        raise SystemExit(
            "source project must contain a project-local profiles.yml; do not use production credentials"
        )
    if not args.no_fallback and args.max_calls < 2:
        raise SystemExit("--max-calls must be at least 2 when the coding-model fallback is enabled")
    if not args.model.strip():
        raise SystemExit("--model must not be empty")

    incident_text = _incident_text(args)
    context_text = None
    if args.business_context:
        context_text = _read_required_text(args.business_context, "business context")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sandbox = (
        Path(args.sandbox).expanduser().resolve()
        if args.sandbox
        else (ROOT / ".work" / f"manual-{stamp}").resolve()
    )
    _prepare_sandbox(source, sandbox, args.force)

    if context_text is not None:
        (sandbox / "BUSINESS_CONTEXT.md").write_text(context_text + "\n", encoding="utf-8")

    _init_snapshot(sandbox)

    try:
        result = run_v4(
            sandbox,
            incident_text,
            args.model,
            max_model_calls=args.max_calls,
            allow_fallback=not args.no_fallback,
        )
        infrastructure_error = None
    except InferenceTransportError as exc:
        result = None
        infrastructure_error = str(exc)

    build = (result or {}).get("final_build") or {}
    build_returncode = build.get("returncode")
    if infrastructure_error:
        execution_status = "infrastructure_error"
    elif build_returncode == 0:
        execution_status = "build_passed_requires_human_approval"
    else:
        execution_status = "build_failed"

    report = {
        "report_version": "2.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_status": execution_status,
        "workflow_mode": "skills_only" if args.no_fallback else "hybrid_skills_with_model_fallback",
        "source_project": str(source),
        "sandbox_project": str(sandbox),
        "source_project_modified": False,
        "deployment_performed": False,
        "human_approval_required": True,
        "incident": incident_text,
        "model": args.model,
        "model_fallback_enabled": not args.no_fallback,
        "max_model_calls": args.max_calls,
        "infrastructure_error": infrastructure_error,
        "workflow": result,
        "diff": _diff(sandbox),
        "interpretation": (
            "DriftDoctor routes high-confidence visible contract patterns through deterministic repair skills and "
            "uses the local coding model only as a bounded fallback for unresolved cases. A successful dbt build is "
            "evidence, not proof of semantic correctness: review the skill/model trajectory, diff, build output, "
            "documented business rules, and project-specific tests before applying the patch."
        ),
    }
    report_path = sandbox / "driftdoctor-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Sandbox: {sandbox}")
    print(f"Approval report: {report_path}")
    if infrastructure_error:
        print(f"Infrastructure error: {infrastructure_error}", file=sys.stderr)
        return 2

    print(f"dbt build return code: {build_returncode}")
    print(f"repair skills: {', '.join((result or {}).get('skills', [])) or 'none'}")
    print(f"model fallback used: {bool((result or {}).get('fallback_used'))}")
    print(f"model calls: {int((result or {}).get('model_calls', 0))}")
    print("No source files were modified and no deployment was performed.")
    if build_returncode != 0:
        print("Repair did not reach a successful dbt build; inspect the approval report.", file=sys.stderr)
        return 1
    print("Build passed, but human approval and project-specific semantic checks are still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
