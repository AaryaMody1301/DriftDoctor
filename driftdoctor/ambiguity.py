from __future__ import annotations

import re
from pathlib import Path

from driftdoctor.v2 import _chat


def _model_stems(root: Path) -> set[str]:
    return {path.stem for path in (root / "models").glob("**/*.sql") if path.is_file()}


def find_ambiguous_missing_ref(root: Path) -> dict | None:
    """Find one missing ref with multiple plausible observed replacement models.

    The function only proposes ambiguity from project structure. It does not choose
    a repair and does not consult benchmark/evaluator code.
    """
    root = root.resolve()
    stems = _model_stems(root)
    ambiguities: list[dict] = []
    for path in sorted((root / "models").glob("**/*.sql")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for missing in re.findall(r"ref\(['\"]([^'\"]+)['\"]\)", text):
            if missing in stems:
                continue
            candidates = sorted(
                stem
                for stem in stems
                if stem.startswith(missing + "_")
                or stem.startswith(missing + "v")
                or missing.startswith(stem + "_")
            )
            if 2 <= len(candidates) <= 8:
                ambiguities.append(
                    {
                        "path": str(path.relative_to(root)),
                        "missing_ref": missing,
                        "candidates": candidates,
                        "content": text,
                    }
                )
    if len(ambiguities) != 1:
        return None
    return ambiguities[0]


def resolve_ambiguous_missing_ref(
    root: Path,
    incident: str,
    context: str,
    model: str,
) -> dict:
    """Use one constrained model decision to resolve an observed ambiguous ref.

    The model can select only an existing candidate or abstain. File editing remains
    deterministic and is performed by the caller after this function returns.
    """
    ambiguity = find_ambiguous_missing_ref(root)
    if ambiguity is None:
        return {"handled": False, "model_calls": 0, "reason": "no single bounded missing-ref ambiguity"}

    candidates = list(ambiguity["candidates"])
    choices = candidates + ["abstain"]
    schema = {
        "type": "object",
        "properties": {
            "selection": {"type": "string", "enum": choices},
            "reason": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["selection", "reason", "evidence"],
    }
    candidate_files = {}
    for stem in candidates:
        path = next((p for p in (root / "models").glob("**/*.sql") if p.is_file() and p.stem == stem), None)
        if path is not None:
            candidate_files[str(path.relative_to(root))] = path.read_text(encoding="utf-8", errors="replace")[:5000]

    decision = _chat(
        model,
        [
            {
                "role": "system",
                "content": (
                    "You are a bounded dependency-resolution agent for a dbt repair workflow. "
                    "A downstream ref points to a model that no longer exists and project structure exposes multiple plausible replacements. "
                    "Choose only when the incident, documented business context, and observed candidate files clearly identify the current dependency. "
                    "Otherwise select abstain. Never invent a model name."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Incident:\n{incident}\n\nBusiness context:\n{context}\n\n"
                    f"Downstream file: {ambiguity['path']}\nMissing ref: {ambiguity['missing_ref']}\n"
                    f"Allowed candidates: {candidates}\n\nCandidate files:\n{candidate_files}\n\n"
                    f"Downstream SQL:\n{ambiguity['content'][:7000]}"
                ),
            },
        ],
        schema,
    )
    selection = str(decision.get("selection", "abstain"))
    if selection not in candidates:
        return {
            "handled": False,
            "model_calls": 1,
            "ambiguity": ambiguity,
            "decision": decision,
            "reason": "agent abstained",
        }

    replacement = re.sub(
        rf"ref\((['\"]){re.escape(ambiguity['missing_ref'])}\1\)",
        f"ref('{selection}')",
        ambiguity["content"],
    )
    return {
        "handled": True,
        "model_calls": 1,
        "ambiguity": ambiguity,
        "decision": decision,
        "patch": {
            "explanation": "Bounded ambiguity resolver selected an observed existing dependency.",
            "files": [{"path": ambiguity["path"], "content": replacement}],
        },
        "root_cause_class": "model_ref_renamed",
    }
