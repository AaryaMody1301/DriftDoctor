from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


def _run(root: Path, command: list[str], timeout: int = 90) -> dict:
    try:
        proc = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
        return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-12000:]}
    except subprocess.TimeoutExpired:
        return {"command": command, "returncode": 124, "stdout": "", "stderr": f"timed out after {timeout}s"}


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def collect_evidence(root: Path) -> dict:
    """Collect deterministic, non-secret evidence available to a normal dbt engineer."""
    root = root.resolve()
    build = _run(root, ["dbt", "build", "--profiles-dir", "."])
    manifest = _read_json(root / "target" / "manifest.json") or {}
    run_results = _read_json(root / "target" / "run_results.json") or {}

    resources = []
    for unique_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") not in {"model", "test"}:
            continue
        resources.append({
            "unique_id": unique_id,
            "resource_type": node.get("resource_type"),
            "name": node.get("name"),
            "path": node.get("original_file_path") or node.get("path"),
            "depends_on": node.get("depends_on", {}).get("nodes", []),
        })

    sources = []
    for unique_id, src in manifest.get("sources", {}).items():
        sources.append({"unique_id": unique_id, "name": src.get("name"), "source_name": src.get("source_name")})

    executions = []
    for result in run_results.get("results", []):
        executions.append({
            "unique_id": result.get("unique_id"),
            "status": result.get("status"),
            "message": result.get("message"),
            "failures": result.get("failures"),
        })

    files = {}
    for pattern in ("models/**/*.sql", "models/**/*.yml", "models/**/*.yaml", "macros/**/*.sql"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                files[str(path.relative_to(root))] = path.read_text(errors="replace")[:12000]

    inputs = {}
    for path in sorted((root / "input").glob("*.csv")):
        with path.open(newline="", errors="replace") as handle:
            rows = list(csv.reader(handle))[:8]
        inputs[str(path.relative_to(root))] = rows

    return {
        "dbt_build": build,
        "resources": resources,
        "sources": sources,
        "executions": executions,
        "project_files": files,
        "input_samples": inputs,
    }


def compact_evidence(evidence: dict, max_chars: int = 26000) -> str:
    text = json.dumps(evidence, indent=2, sort_keys=True)
    return text[:max_chars]
