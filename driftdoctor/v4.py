from __future__ import annotations

import time
from pathlib import Path

from driftdoctor.ambiguity import resolve_ambiguous_missing_ref
from driftdoctor.contract_checks import semantic_concerns
from driftdoctor.repair_skills import propose_contract_patch
from driftdoctor.v2 import _business_context, _run_build


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
            reason = "new files are not allowed by the repair guard"
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
    escalation_required: bool = False,
) -> dict:
    if diagnosis is None:
        diagnosis = {
            "root_cause_class": prediction,
            "hypothesis": (
                "Visible contract and project structure matched deterministic repair skills."
                if prediction != "unknown"
                else "The bounded workflow could not establish a verified repair from visible evidence."
            ),
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
        "escalation_required": escalation_required,
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
    """Run the final selective-agency DriftDoctor workflow.

    1. Capture the broken-state dbt signal.
    2. Apply deterministic skills only when the visible contract determines a safe edit.
    3. If exactly one bounded dependency ambiguity remains, let a constrained agent
       choose only among observed candidate models or abstain.
    4. Verify with dbt + visible contract checks.
    5. Escalate to a human instead of using the historically weak open-ended coding
       fallback when the bounded workflow cannot verify a repair.

    Hidden benchmark oracle/reference-repair code is never consulted inside this workflow.
    `max_model_calls` is retained for CLI/evaluation compatibility; the final bounded
    agent currently uses at most one logical model call.
    """
    del max_model_calls
    root = root.resolve()
    started = time.monotonic()
    context = _business_context(root)
    trajectory: list[dict] = []

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
            escalation_required=build.get("returncode") != 0 or bool(concerns),
        )

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
        decision = ambiguity.get("decision") or {}
        diagnosis = {
            "root_cause_class": ambiguity.get("root_cause_class", "model_ref_renamed"),
            "hypothesis": "A missing dependency had multiple observed candidates; a bounded agent selected from those candidates.",
            "evidence": list(decision.get("evidence") or [])
            + [f"agent_selection:{decision.get('selection', 'unknown')}"],
            "files_to_change": [item["path"] for item in ambiguity_patch.get("files", [])],
        }
        if build.get("returncode") == 0 and not concerns:
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

    trajectory.append(
        {
            "stage": "human_escalation",
            "reason": (
                ambiguity.get("reason")
                or "No verified bounded repair was available; open-ended autonomous editing is intentionally disabled."
            ),
        }
    )
    return _result(
        model=model,
        started=started,
        prediction=skill_prediction,
        skills=skills,
        files=skill_patch.get("files", []),
        build=build,
        concerns=concerns,
        trajectory=trajectory,
        model_calls=ambiguity_calls,
        fallback_used=ambiguity_calls > 0,
        fallback_mode="bounded_ambiguity_resolver" if ambiguity_calls else None,
        escalation_required=True,
    )
