from __future__ import annotations

import time
from pathlib import Path

from driftdoctor.repair_skills import propose_contract_patch
from driftdoctor.v2 import _business_context, _run_build
from driftdoctor.v3 import _apply_existing_only, run_v3, semantic_concerns


def _skill_result(
    *,
    model: str,
    started: float,
    skill_prediction: str,
    skills: list[str],
    skill_patch: dict,
    build: dict,
    concerns: list[str],
    trajectory: list[dict],
) -> dict:
    return {
        "system": "driftdoctor-v0.4-hybrid-skills",
        "model": model,
        "model_calls": 0,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "diagnosis": {
            "root_cause_class": skill_prediction,
            "hypothesis": "Visible contract and project structure matched deterministic repair skills.",
            "evidence": [f"repair_skill:{name}" for name in skills],
            "files_to_change": [item["path"] for item in skill_patch.get("files", [])],
        },
        "skill_root_cause_class": skill_prediction,
        "final_build": build,
        "remaining_contract_concerns": concerns,
        "skills": skills,
        "fallback_used": False,
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
    """Run deterministic contract skills first, then optionally use v3 fallback.

    Specialized skills are preferred when the visible project and business contract
    determine a high-confidence edit. The local coding model remains available for
    ambiguous cases or for correcting a skill patch that does not build. Hidden
    benchmark oracle code is never consulted inside this workflow.
    """
    root = root.resolve()
    started = time.monotonic()
    context = _business_context(root)
    trajectory: list[dict] = []

    skill_patch = propose_contract_patch(root, context)
    skill_prediction = skill_patch.get("root_cause_class", "unknown")
    skills = list(skill_patch.get("skills") or [])
    build = _run_build(root)
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
            return _skill_result(
                model=model,
                started=started,
                skill_prediction=skill_prediction,
                skills=skills,
                skill_patch=skill_patch,
                build=build,
                concerns=[],
                trajectory=trajectory,
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
        return _skill_result(
            model=model,
            started=started,
            skill_prediction=skill_prediction,
            skills=skills,
            skill_patch=skill_patch,
            build=build,
            concerns=concerns,
            trajectory=trajectory,
        )

    fallback = run_v3(root, incident, model, max_model_calls=max_model_calls)
    fallback_diagnosis = fallback.get("diagnosis") or {}
    if skill_prediction != "unknown":
        fallback_diagnosis = dict(fallback_diagnosis)
        fallback_diagnosis.setdefault("skill_root_cause_class", skill_prediction)

    trajectory.extend(fallback.get("trajectory") or [])
    return {
        "system": "driftdoctor-v0.4-hybrid-skills",
        "model": model,
        "model_calls": int(fallback.get("model_calls", 0)),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "diagnosis": fallback_diagnosis,
        "skill_root_cause_class": skill_prediction,
        "final_build": fallback.get("final_build"),
        "remaining_contract_concerns": fallback.get("remaining_contract_concerns") or [],
        "skills": skills,
        "fallback_used": True,
        "trajectory": trajectory,
    }
