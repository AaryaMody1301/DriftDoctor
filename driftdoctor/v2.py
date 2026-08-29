from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from driftdoctor.evidence import collect_evidence, compact_evidence

ROOT_CAUSES = [
    "source_column_renamed", "source_column_removed", "source_type_changed",
    "model_ref_renamed", "join_cardinality_regression", "nullability_regression",
    "accepted_value_drift", "macro_signature_changed", "grain_regression",
    "timezone_semantics_changed", "business_rule_regression",
    "multi_fault_schema_and_type_drift", "unknown",
]

DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause_class": {"type": "string", "enum": ROOT_CAUSES},
        "hypothesis": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "files_to_change": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["root_cause_class", "hypothesis", "evidence", "files_to_change"],
}

PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    "required": ["explanation", "files"],
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["accept", "retry"]},
        "reason": {"type": "string"},
        "suggested_focus": {"type": "string"},
    },
    "required": ["verdict", "reason", "suggested_focus"],
}


class InferenceTransportError(RuntimeError):
    """Raised when local Ollama inference does not return after bounded retries."""


def _chat(
    model: str,
    messages: list[dict],
    schema: dict,
    timeout: int = 600,
    transport_retries: int = 1,
) -> dict:
    """Run one logical model call with bounded transport-only retry.

    A retry is used only when the local HTTP transport times out/fails before a
    response is received. It does not alter prompts, schemas, temperature, or
    the logical model-call budget used by the experiment.
    """
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "format": schema,
        "options": {"temperature": 0},
    }).encode()
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
    last_error: Exception | None = None

    for attempt in range(transport_retries + 1):
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.load(response)
            return json.loads(data["message"]["content"])
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt >= transport_retries:
                break
            time.sleep(2)

    raise InferenceTransportError(
        f"local inference transport failed after {transport_retries + 1} attempts: {last_error}"
    )


def _business_context(root: Path) -> str:
    path = root / "BUSINESS_CONTEXT.md"
    return path.read_text(errors="replace") if path.exists() else "No explicit business context file was provided."


def _run_build(root: Path, timeout: int = 120) -> dict:
    try:
        proc = subprocess.run(
            ["dbt", "build", "--profiles-dir", "."], cwd=root,
            text=True, capture_output=True, timeout=timeout,
        )
        return {"returncode": proc.returncode, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-12000:]}
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "stdout": "", "stderr": f"timed out after {timeout}s"}


def _apply_patch(root: Path, patch: dict) -> list[dict]:
    applied = []
    for item in patch.get("files", []):
        raw = str(item.get("path", ""))
        content = str(item.get("content", ""))
        target = (root / raw).resolve()
        allowed = root in target.parents and (raw.startswith("models/") or raw.startswith("macros/"))
        reason = None
        if not allowed:
            reason = "path is outside editable models/macros scope"
        elif len(content.strip()) < 12:
            reason = "replacement is implausibly short"
        elif "complete replacement contents" in content.lower() or "```" in content:
            reason = "replacement contains placeholder/markdown fencing"
        if reason:
            applied.append({"path": raw, "applied": False, "reason": reason})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        before = target.read_text(errors="replace") if target.exists() else ""
        if before == content:
            applied.append({"path": raw, "applied": False, "reason": "no change"})
            continue
        target.write_text(content, encoding="utf-8")
        applied.append({"path": raw, "applied": True})
    return applied


def run_v2(root: Path, incident: str, model: str, max_model_calls: int = 14, semantic_review: bool = True) -> dict:
    root = root.resolve()
    started = time.monotonic()
    calls = 0
    trajectory: list[dict] = []
    context = _business_context(root)
    evidence = collect_evidence(root)

    diagnosis = _chat(model, [
        {"role": "system", "content": "Diagnose this dbt incident from visible evidence only. Choose the closest root-cause taxonomy label. Do not propose hidden requirements."},
        {"role": "user", "content": f"Incident:\n{incident}\n\nDocumented business rules:\n{context}\n\nEvidence:\n{compact_evidence(evidence)}"},
    ], DIAGNOSIS_SCHEMA)
    calls += 1
    trajectory.append({"stage": "diagnose", "output": diagnosis})

    patch = _chat(model, [
        {"role": "system", "content": "Produce the smallest safe complete-file replacements needed to fix the diagnosed dbt incident. Return actual file contents, never placeholders. Preserve public contracts and follow BUSINESS_CONTEXT exactly."},
        {"role": "user", "content": f"Incident:\n{incident}\n\nBusiness context:\n{context}\n\nDiagnosis:\n{json.dumps(diagnosis)}\n\nProject evidence:\n{compact_evidence(evidence)}"},
    ], PATCH_SCHEMA)
    calls += 1
    applied = _apply_patch(root, patch)
    build = _run_build(root)
    trajectory.append({"stage": "patch", "output": patch, "applied": applied, "build": build})

    # Compilation/runtime retry: deterministic build feedback creates a new signal.
    if build["returncode"] != 0 and calls < max_model_calls:
        latest = collect_evidence(root)
        repair = _chat(model, [
            {"role": "system", "content": "The previous repair did not build. Use the concrete dbt failure to return corrected complete-file replacements. Do not repeat an unchanged patch."},
            {"role": "user", "content": f"Incident:\n{incident}\n\nBusiness context:\n{context}\n\nPrevious diagnosis:\n{json.dumps(diagnosis)}\n\nFailed build:\n{json.dumps(build)}\n\nCurrent project:\n{compact_evidence(latest)}"},
        ], PATCH_SCHEMA)
        calls += 1
        applied2 = _apply_patch(root, repair)
        build = _run_build(root)
        trajectory.append({"stage": "build_retry", "output": repair, "applied": applied2, "build": build})

    reviews = 0
    if semantic_review and calls < max_model_calls:
        latest = collect_evidence(root)
        review = _chat(model, [
            {"role": "system", "content": "Act as an adversarial analytics engineer. Check the current SQL/YAML against the incident and documented business rules. A green dbt build is insufficient for semantic correctness. Request retry only with a concrete visible mismatch."},
            {"role": "user", "content": f"Incident:\n{incident}\n\nBusiness context:\n{context}\n\nDiagnosis:\n{json.dumps(diagnosis)}\n\nCurrent evidence:\n{compact_evidence(latest)}"},
        ], REVIEW_SCHEMA)
        calls += 1
        trajectory.append({"stage": "semantic_review", "output": review})
        if review.get("verdict") == "retry" and calls < max_model_calls:
            reviews += 1
            repair = _chat(model, [
                {"role": "system", "content": "Correct the specific verifier concern with the smallest complete-file replacement. Follow documented business rules and do not repeat unchanged content."},
                {"role": "user", "content": f"Incident:\n{incident}\n\nBusiness context:\n{context}\n\nVerifier concern:\n{json.dumps(review)}\n\nCurrent evidence:\n{compact_evidence(latest)}"},
            ], PATCH_SCHEMA)
            calls += 1
            applied3 = _apply_patch(root, repair)
            build = _run_build(root)
            trajectory.append({"stage": "semantic_retry", "output": repair, "applied": applied3, "build": build})

    return {
        "system": "driftdoctor-v0.2-review" if semantic_review else "driftdoctor-v0.2-no-review",
        "model": model,
        "model_calls": calls,
        "semantic_retries": reviews,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "diagnosis": diagnosis,
        "final_build": build,
        "trajectory": trajectory,
    }
