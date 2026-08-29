from __future__ import annotations

import time
from pathlib import Path

from driftdoctor.ambiguity import resolve_ambiguous_missing_ref
from driftdoctor.repair_skills import propose_contract_patch
from driftdoctor.v2 import _business_context, _run_build
from driftdoctor.v3 import run_v3, semantic_concerns


def _apply_existing_only(root: Path, patch: dict) -> list[dict]:
    """Apply complete-file replacements only to existing model/macro files."""
    root = root.resolve()
    applied: list[dict] = []
    for item in patch.get("files", []):
        raw = str(item.get("path", ""))
        content = str(item.get("content", ""))
        target = (root / raw).resolve()
        reason = None
        if root not in target.parents:
            reason = "path escapes workspace"
        elif not (raw.startswith("models/") or raw.startswith("macros/")):
            reason = "path is outside editable models/macros scope"
        elif not target.is_file():
            reason = "new files are not allowed by the contract-skill guard"
        elif len(content.strip()) < 12:
            reason = "replacement is implausibly short"
        elif "```" in content or "complete replacement contents" in content.lower():
            reason = "replacement contains placeholder/markdown fencing"

        if reason:
            applied.append({"path": raw, "applied": False, "reason": reason})
            continue

        before = target.read_text(encoding="utf-8", errors="replace")
        if before == content:
            applied.append({"path": raw, "applied": False, "reason": "no change"})
            continue
        target.write_text(content, encoding="utf-8")
        applied.append({"path": raw, "applied": True})
    return applied


def _result(
    *,
    model: str,
    started: float,
    prediction: str,
    skills: list[str],
    files: list[dict],
    build: dict,
    concerns: list[str],
    trajectory: list[dict],
    model_calls: int,
    fallback_used: bool,
    fallback_mode: str | None = None,
    diagnosis: dict | None = None,
) -> dict:
    if diagnosis is None:
        diagnosis = {
            "root_cause_class": prediction,
            "hypothesis": "Visible contract and project structure matched deterministic repair skills.",
            "evidence": [f"repair_skill:{name}" for name in skills],
            "files_to_change": [item["path"] for item in files],
        }
    return {
        "system": "driftdoctor-v0.5-selective-agency",
        "model": model,
        "model_calls": model_calls,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "diagnosis": diagnosis,
        "skill_root_cause_class": prediction,
        "final_build": build,
        "remaining_contract_concerns": concerns,
        "skills": skills,
        "fallback_used": fallback_used,
        "fallback_mode": fallback_mode,
        "trajectory": trajectory,
    }


def run_v4(
    root: Path,
    incident: str,
    model: str,
    max_model_calls: int = 14,
    *,
    allow_fallback: bool = True,
) -> dict:
    """Run selective agency: deterministic skills first, bounded agents for ambiguity.

    High-confidence contract repairs remain deterministic. If the project exposes one
    bounded dependency ambiguity, a constrained agent may choose only from observed
    candidate models or abstain. Open-ended v3 repair remains the last fallback.
    Hidden benchmark oracle/reference-repair code is never consulted inside this workflow.
    """
    root = root.resolve()
    started = time.monotonic()
    context = _business_context(root)
    trajectory: list[dict] = []

    # Record the broken-state executable evidence before proposing a repair. This makes
    # the final trajectory show the actual before/after verification signal.
    initial_build = _run_build(root)
    trajectory.append({"stage": "initial_build", "build": initial_build})

    skill_patch = propose_contract_patch(root, context)
    skill_prediction = skill_patch.get("root_cause_class", "unknown")
    skills = list(skill_patch.get("skills") or [])
    build = initial_build
    concerns: list[str] = []

    if skill_patch.get("files"):
        applied = _apply_existing_only(root, skill_patch)
        build = _run_build(root)
        concerns = semantic_concerns(root, context) if build.get("returncode") == 0 else []
        trajectory.append(
            {
                "stage": "contract_skills",
                "skills": skills,
                "output": skill_patch,
                "applied": applied,
                "build": build,
                "remaining_contract_concerns": concerns,
            }
        )
        if build.get("returncode") == 0 and not concerns:
            return _result(
                model=model,
                started=started,
                prediction=skill_prediction,
                skills=skills,
                files=skill_patch.get("files", []),
                build=build,
                concerns=[],
                trajectory=trajectory,
                model_calls=0,
                fallback_used=False,
            )
    else:
        concerns = semantic_concerns(root, context) if build.get("returncode") == 0 else []
        trajectory.append(
            {
                "stage": "contract_skills",
                "skills": [],
                "output": skill_patch,
                "applied": [],
                "build": build,
                "remaining_contract_concerns": concerns,
            }
        )

    if not allow_fallback:
        return _result(
            model=model,
            started=started,
            prediction=skill_prediction,
            skills=skills,
            files=skill_patch.get("files", []),
            build=build,
            concerns=concerns,
            trajectory=trajectory,
            model_calls=0,
            fallback_used=False,
        )

    # First agentic fallback: resolve a bounded observed ambiguity rather than asking a
    # coding model to regenerate whole files. The model can only select an existing
    # candidate dependency or abstain; the executor and verifier remain deterministic.
    ambiguity = resolve_ambiguous_missing_ref(root, incident, context, model)
    ambiguity_calls = int(ambiguity.get("model_calls", 0))
    if ambiguity_calls:
        trajectory.append(
            {
                "stage": "ambiguity_resolver",
                "ambiguity": ambiguity.get("ambiguity"),
                "decision": ambiguity.get("decision"),
                "handled": bool(ambiguity.get("handled")),
                "reason": ambiguity.get("reason"),
            }
        )
    if ambiguity.get("handled"):
        ambiguity_patch = ambiguity["patch"]
        applied = _apply_existing_only(root, ambiguity_patch)
        build = _run_build(root)
        concerns = semantic_concerns(root, context) if build.get("returncode") == 0 else []
        trajectory.append(
            {
                "stage": "ambiguity_patch",
                "output": ambiguity_patch,
                "applied": applied,
                "build": build,
                "remaining_contract_concerns": concerns,
            }
        )
        if build.get("returncode") == 0 and not concerns:
            decision = ambiguity.get("decision") or {}
            diagnosis = {
                "root_cause_class": ambiguity.get("root_cause_class", "model_ref_renamed"),
                "hypothesis": "A missing dependency had multiple observed candidates; a bounded agent selected the documented current model.",
                "evidence": list(decision.get("evidence") or [])
                + [f"agent_selection:{decision.get('selection', 'unknown')}"],
                "files_to_change": [item["path"] for item in ambiguity_patch.get("files", [])],
            }
            return _result(
                model=model,
                started=started,
                prediction=diagnosis["root_cause_class"],
                skills=skills,
                files=ambiguity_patch.get("files", []),
                build=build,
                concerns=[],
                trajectory=trajectory,
                model_calls=ambiguity_calls,
                fallback_used=True,
                fallback_mode="bounded_ambiguity_resolver",
                diagnosis=diagnosis,
            )

    # Last resort: open-ended contract-guided coding agent. This remains bounded and is
    # only used after deterministic skills and the narrow ambiguity resolver fail.
    fallback = run_v3(root, incident, model, max_model_calls=max_model_calls)
    fallback_diagnosis = fallback.get("diagnosis") or {}
    if skill_prediction != "unknown":
        fallback_diagnosis = dict(fallback_diagnosis)
        fallback_diagnosis.setdefault("skill_root_cause_class", skill_prediction)

    trajectory.extend(fallback.get("trajectory") or [])
    return {
        "system": "driftdoctor-v0.5-selective-agency",
        "model": model,
        "model_calls": ambiguity_calls + int(fallback.get("model_calls", 0)),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "diagnosis": fallback_diagnosis,
        "skill_root_cause_class": skill_prediction,
        "final_build": fallback.get("final_build"),
        "remaining_contract_concerns": fallback.get("remaining_contract_concerns") or [],
        "skills": skills,
        "fallback_used": True,
        "fallback_mode": "contract_guided_coding_agent",
        "trajectory": trajectory,
    }
