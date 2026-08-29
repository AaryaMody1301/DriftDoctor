from __future__ import annotations

import re
from pathlib import Path

from driftdoctor.v2 import _chat

_REF_RE = re.compile(r"ref\s*\(\s*(['\"])(?P<name>[^'\"]+)\1\s*\)")


def _model_paths(root: Path) -> dict[str, list[Path]]:
    paths: dict[str, list[Path]] = {}
    for path in (root / "models").glob("**/*.sql"):
        if path.is_file():
            paths.setdefault(path.stem, []).append(path)
    return paths


def _replace_ref_name(content: str, missing: str, selection: str) -> tuple[str, int]:
    spans = [
        match.span("name")
        for match in _REF_RE.finditer(content)
        if match.group("name") == missing
    ]
    replacement = content
    for start, end in reversed(spans):
        replacement = replacement[:start] + selection + replacement[end:]
    return replacement, len(spans)


def find_ambiguous_missing_ref(root: Path) -> dict | None:
    """Find one missing ref with multiple plausible observed replacement models.

    The function only proposes ambiguity from project structure. It does not choose
    a repair and does not consult benchmark/evaluator code. Repeated occurrences of
    the same missing ref in one file count as one logical ambiguity.
    """
    root = root.resolve()
    model_paths = _model_paths(root)
    stems = set(model_paths)
    ambiguities: dict[tuple[str, str], dict] = {}
    for path in sorted((root / "models").glob("**/*.sql")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _REF_RE.finditer(text):
            missing = match.group("name")
            if missing in stems:
                continue
            candidates = sorted(
                stem
                for stem in stems
                if len(model_paths[stem]) == 1
                and (
                    stem.startswith(missing + "_")
                    or re.match(rf"^{re.escape(missing)}v\d", stem)
                    or missing.startswith(stem + "_")
                )
            )
            if 2 <= len(candidates) <= 8:
                relative = str(path.relative_to(root))
                ambiguities[(relative, missing)] = {
                    "path": relative,
                    "missing_ref": missing,
                    "candidates": candidates,
                    "content": text,
                }
    if len(ambiguities) != 1:
        return None
    return next(iter(ambiguities.values()))


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
    root = root.resolve()
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
    model_paths = _model_paths(root)
    candidate_files = {}
    for stem in candidates:
        paths = model_paths.get(stem, [])
        if len(paths) == 1:
            path = paths[0]
            candidate_files[str(path.relative_to(root))] = path.read_text(
                encoding="utf-8", errors="replace"
            )[:5000]

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
            "reason": "agent abstained or returned an invalid candidate",
        }

    replacement, replacements = _replace_ref_name(
        ambiguity["content"], ambiguity["missing_ref"], selection
    )
    if replacements == 0 or replacement == ambiguity["content"]:
        return {
            "handled": False,
            "model_calls": 1,
            "ambiguity": ambiguity,
            "decision": decision,
            "reason": "the bounded reference could not be replaced safely",
        }
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
