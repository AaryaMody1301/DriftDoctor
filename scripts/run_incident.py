#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from driftdoctor.v2 import InferenceTransportError  # noqa: E402
from driftdoctor.v4 import run_v4  # noqa: E402

SANDBOX_MARKER = ".driftdoctor-sandbox"
_ALLOWED_DUCKDB_TARGET_KEYS = {"type", "path", "schema", "threads"}
_REMOTE_PATH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


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


def _validate_project_tree(source: Path) -> None:
    """Reject project shapes that can escape the disposable-copy boundary."""
    for path in source.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"source project must not contain symlinks: {path}")
    python_models = sorted((source / "models").glob("**/*.py")) if (source / "models").is_dir() else []
    if python_models:
        relative = ", ".join(str(path.relative_to(source)) for path in python_models[:3])
        raise SystemExit(
            "judge CLI accepts SQL dbt models only; Python models can execute arbitrary local code: "
            + relative
        )


def _copy_project(source: Path, sandbox: Path) -> None:
    ignored = shutil.ignore_patterns(
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "target",
        "logs",
        "dbt_packages",
        "__pycache__",
        ".work",
        SANDBOX_MARKER,
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


def _validate_local_duckdb_profile(source: Path) -> None:
    """Allow only a simple, local, disposable DuckDB target.

    A DuckDB adapter can still address MotherDuck, absolute files, attached remote
    databases, cloud secrets, extensions, or plugins. The judge CLI deliberately
    rejects those capabilities so copying a project actually confines database state
    to the sandbox.
    """
    try:
        project = yaml.safe_load((source / "dbt_project.yml").read_text(encoding="utf-8")) or {}
        profiles = yaml.safe_load((source / "profiles.yml").read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(f"could not parse project-local dbt YAML safely: {exc}") from exc

    if not isinstance(project, dict) or not isinstance(profiles, dict):
        raise SystemExit("dbt_project.yml and profiles.yml must contain YAML mappings")
    for hook_name in ("on-run-start", "on-run-end"):
        if project.get(hook_name):
            raise SystemExit(
                f"judge CLI rejects {hook_name} hooks because they can run side-effecting SQL outside model builds"
            )

    profile_name = project.get("profile")
    if not isinstance(profile_name, str) or profile_name not in profiles:
        raise SystemExit("dbt_project.yml must name a profile present in the project-local profiles.yml")
    profile = profiles.get(profile_name) or {}
    if not isinstance(profile, dict):
        raise SystemExit("the selected dbt profile must be a YAML mapping")
    target_name = profile.get("target")
    outputs = profile.get("outputs") or {}
    target = outputs.get(target_name) if isinstance(outputs, dict) else None
    if not isinstance(target_name, str) or not isinstance(target, dict):
        raise SystemExit("the selected dbt profile target must exist under outputs")

    adapter = target.get("type")
    if str(adapter).strip().lower() != "duckdb":
        raise SystemExit(
            "refusing non-DuckDB target: the judge CLI only runs disposable local DuckDB profiles"
        )

    unexpected = sorted(set(target) - _ALLOWED_DUCKDB_TARGET_KEYS)
    if unexpected:
        raise SystemExit(
            "refusing DuckDB target capabilities outside the local judge profile: "
            + ", ".join(unexpected)
        )

    if "threads" in target:
        threads = target["threads"]
        if isinstance(threads, bool) or not isinstance(threads, int) or threads < 1:
            raise SystemExit("DuckDB target threads must be a positive integer")
    if "schema" in target and not isinstance(target["schema"], str):
        raise SystemExit("DuckDB target schema must be a string")

    if "path" not in target:
        return  # dbt-duckdb defaults to an in-memory database.
    raw_path = target.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SystemExit("DuckDB target path must be a non-empty string or be omitted for in-memory mode")
    raw_path = raw_path.strip()
    if raw_path == ":memory:":
        return
    if "{{" in raw_path or "{%" in raw_path:
        raise SystemExit("DuckDB target path must not be generated from Jinja or environment variables")
    if _REMOTE_PATH_RE.match(raw_path):
        raise SystemExit("DuckDB target path must be a relative local file, not a URI or remote connection string")

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        raise SystemExit("DuckDB target path must be relative so the copied sandbox owns the database state")
    resolved = (source / candidate).resolve()
    if source.resolve() not in resolved.parents:
        raise SystemExit("DuckDB target path must stay inside the project directory")


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
    """Return a reviewable source/config diff without generated DuckDB state."""
    proc = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--",
            ".",
            ":(glob,exclude)**/*.duckdb",
            ":(glob,exclude)**/*.duckdb.wal",
            ":(exclude)driftdoctor-report.json",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run DriftDoctor against a disposable copy of a trusted local dbt project and emit "
            "an approval-ready report. The source project is never modified."
        )
    )
    parser.add_argument("--project", required=True, help="Path to the trusted source dbt project")
    incident = parser.add_mutually_exclusive_group(required=True)
    incident.add_argument("--incident", help="Incident description")
    incident.add_argument("--incident-file", help="Text file containing the incident description")
    parser.add_argument(
        "--business-context",
        help="Optional Markdown/text file containing documented business rules to copy into BUSINESS_CONTEXT.md",
    )
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--max-calls", type=int, default=1)
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Use deterministic contract repair skills only; never invoke the bounded ambiguity-resolver agent.",
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
    _validate_project_tree(source)
    _validate_local_duckdb_profile(source)
    if not args.no_fallback and args.max_calls != 1:
        raise SystemExit("--max-calls must be exactly 1 when the bounded ambiguity-resolver agent is enabled")
    if args.no_fallback and args.max_calls < 0:
        raise SystemExit("--max-calls must not be negative")
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
    except (InferenceTransportError, ValueError) as exc:
        result = None
        infrastructure_error = str(exc)

    build = (result or {}).get("final_build") or {}
    build_returncode = build.get("returncode")
    escalation_required = bool((result or {}).get("escalation_required"))
    concerns = list((result or {}).get("remaining_contract_concerns") or [])
    if infrastructure_error:
        execution_status = "infrastructure_error"
    elif escalation_required or concerns:
        execution_status = "human_escalation_required"
    elif build_returncode == 0:
        execution_status = "locally_verified_requires_human_approval"
    else:
        execution_status = "build_failed"

    report = {
        "report_version": "3.1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_status": execution_status,
        "workflow_mode": "skills_only" if args.no_fallback else "selective_agency",
        "source_project": str(source),
        "sandbox_project": str(sandbox),
        "source_project_modified": False,
        "deployment_performed": False,
        "human_approval_required": True,
        "human_escalation_required": escalation_required,
        "incident": incident_text,
        "model": args.model,
        "ambiguity_agent_enabled": not args.no_fallback,
        "max_model_calls": args.max_calls,
        "infrastructure_error": infrastructure_error,
        "workflow": result,
        "diff": _diff(sandbox),
        "interpretation": (
            "DriftDoctor uses deterministic skills when the visible contract determines a safe repair, and a bounded "
            "agent only when one explicit dependency ambiguity remains. The agent can select only from observed candidates "
            "or abstain. Unsupported ambiguity escalates to a human rather than triggering open-ended autonomous editing. "
            "A successful local build is evidence, not proof of production semantic correctness; review the trajectory, diff, "
            "business rules, project-specific checks, and approval boundary before applying any change."
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
    print(f"bounded agent used: {bool((result or {}).get('fallback_used'))}")
    print(f"model calls: {int((result or {}).get('model_calls', 0))}")
    print("No source files were modified and no deployment was performed.")
    if escalation_required or concerns:
        print("No bounded verified repair was available; human escalation is required.", file=sys.stderr)
        return 1
    if build_returncode != 0:
        print("Repair did not reach a successful dbt build; inspect the approval report.", file=sys.stderr)
        return 1
    print("Local checks passed, but human approval and project-specific semantic checks are still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
