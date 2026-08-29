from __future__ import annotations

import csv
import re
from pathlib import Path


SKILL_ROOT_CAUSE = {
    "source_alias": "source_column_renamed",
    "derived_display_name": "source_column_removed",
    "safe_numeric": "source_type_changed",
    "retarget_ref": "model_ref_renamed",
    "latest_dimension": "join_cardinality_regression",
    "required_identifier": "nullability_regression",
    "categorical_mapping": "accepted_value_drift",
    "macro_interface": "macro_signature_changed",
    "latest_record": "grain_regression",
    "timezone_conversion": "timezone_semantics_changed",
    "business_formula": "business_rule_regression",
}

IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


def _project_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for pattern in ("models/**/*.sql", "models/**/*.yml", "models/**/*.yaml", "macros/**/*.sql"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8", errors="replace")
    return files


def _input_headers(root: Path) -> set[str]:
    headers: set[str] = set()
    for path in sorted((root / "input").glob("*.csv")):
        with path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle)
            try:
                headers.update(cell.strip() for cell in next(reader))
            except StopIteration:
                pass
    return headers


def _model_stems(root: Path) -> set[str]:
    return {path.stem for path in (root / "models").glob("**/*.sql") if path.is_file()}


def _replace_file(files: dict[str, str], path: str, content: str, skills: list[str], skill: str) -> None:
    if content != files[path]:
        files[path] = content
        if skill not in skills:
            skills.append(skill)


def _quoted_identifiers(text: str) -> list[str]:
    return re.findall(rf"`({IDENTIFIER})`", text)


def _declared_contract_fields(context: str) -> list[str]:
    fields: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", context):
        lower = sentence.lower()
        if "contract" in lower or "must expose" in lower:
            for identifier in _quoted_identifiers(sentence):
                if identifier not in fields:
                    fields.append(identifier)
    return fields


def _explicitly_derived_fields(context: str) -> set[str]:
    """Return contract fields whose value is explicitly defined by the business context.

    An explicit derivation must outrank fuzzy source-header matching. Otherwise a field
    such as `owner_display` can be incorrectly aliased from `owner_id` merely because
    both identifiers share the `owner` token.
    """
    derived: set[str] = set()
    for match in re.finditer(
        rf"`({IDENTIFIER})`\s+is\s+(?:the\s+)?(?:trimmed\s+concatenation|derived|computed|calculated)\b",
        context,
        flags=re.IGNORECASE,
    ):
        derived.add(match.group(1).lower())
    return derived


def _semantic_candidates(target: str, headers: set[str]) -> list[str]:
    """Rank source headers by identifier shape without knowing domain-specific names."""
    target_parts = [part for part in target.lower().split("_") if part]
    scored: list[tuple[int, str]] = []
    for header in headers:
        parts = [part for part in header.lower().split("_") if part]
        if not parts or header.lower() == target.lower():
            continue
        score = len(set(target_parts) & set(parts))
        if target_parts and parts and target_parts[-1] == parts[-1]:
            score += 3
        if score:
            scored.append((score, header))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    return sorted(header for score, header in scored if score == best)


def _source_alias(files: dict[str, str], headers: set[str], context: str, skills: list[str]) -> None:
    lower_headers = {h.lower() for h in headers}
    derived_fields = _explicitly_derived_fields(context)
    for target in _declared_contract_fields(context):
        if target.lower() in lower_headers or target.lower() in derived_fields:
            continue
        candidates = _semantic_candidates(target, headers)
        if len(candidates) != 1:
            continue
        candidate = candidates[0]
        for path, text in list(files.items()):
            if not path.endswith(".sql") or "source(" not in text or target not in text:
                continue
            replacement = re.sub(
                rf"(?m)^(\s*){re.escape(target)}(\s*,?)$",
                rf"\1{candidate} as {target}\2",
                text,
            )
            _replace_file(files, path, replacement, skills, "source_alias")


def _derived_display_name(files: dict[str, str], headers: set[str], context: str, skills: list[str]) -> None:
    match = re.search(
        rf"`(?P<out>{IDENTIFIER})`\s+is\s+the\s+trimmed\s+concatenation\s+of\s+`(?P<first>{IDENTIFIER})`.*?`(?P<last>{IDENTIFIER})`",
        context,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return
    output, first, last = match.group("out"), match.group("first"), match.group("last")
    lower_headers = {h.lower() for h in headers}
    if not {first.lower(), last.lower()}.issubset(lower_headers):
        return
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or output not in text:
            continue
        replacement = re.sub(
            rf"(?m)^(\s*){re.escape(output)}(\s*,?)$",
            rf"\1trim({first} || ' ' || {last}) as {output}\2",
            text,
        )
        _replace_file(files, path, replacement, skills, "derived_display_name")


def _safe_numeric(files: dict[str, str], context: str, skills: list[str]) -> None:
    ctx = context.lower()
    if "numeric" not in ctx or "null" not in ctx:
        return
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text:
            continue
        replacement = re.sub(
            rf"\b({IDENTIFIER}_text)\s*\*\s*1(?:\.0+)?\s+as\s+({IDENTIFIER})",
            r"try_cast(\1 as decimal(18,2)) as \2",
            text,
            flags=re.IGNORECASE,
        )
        _replace_file(files, path, replacement, skills, "safe_numeric")


def _retarget_missing_refs(root: Path, files: dict[str, str], skills: list[str]) -> None:
    stems = _model_stems(root)
    for path, text in list(files.items()):
        if not path.endswith(".sql"):
            continue
        replacement = text
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
            if len(candidates) == 1:
                replacement = re.sub(
                    rf"ref\((['\"]){re.escape(missing)}\1\)",
                    f"ref('{candidates[0]}')",
                    replacement,
                )
        _replace_file(files, path, replacement, skills, "retarget_ref")


def _greatest_field(context: str) -> str | None:
    match = re.search(rf"greatest\s+`({IDENTIFIER})`", context, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _latest_dimension(files: dict[str, str], context: str, skills: list[str]) -> None:
    order_field = _greatest_field(context)
    if not order_field or "slowly changing" not in context.lower():
        return
    join_re = re.compile(
        rf"left\s+join\s+(\{{\{{\s*source\([^\n]+?\)\s*\}}\}})\s+({IDENTIFIER})\s*\n\s*on\s+({IDENTIFIER})\.({IDENTIFIER})\s*=\s*\2\.\4",
        re.IGNORECASE,
    )
    for path, text in list(files.items()):
        if not path.endswith(".sql"):
            continue
        match = join_re.search(text)
        if not match:
            continue
        source_expr, dim_alias, fact_alias, join_key = match.groups()
        cte_name = "driftdoctor_latest_dimension"
        cte = (
            f"with {cte_name} as (\n"
            "    select *\n"
            f"    from {source_expr}\n"
            "    qualify row_number() over (\n"
            f"        partition by {join_key} order by {order_field} desc\n"
            "    ) = 1\n"
            ")\n"
        )
        body = join_re.sub(
            f"left join {cte_name} {dim_alias}\n  on {fact_alias}.{join_key} = {dim_alias}.{join_key}",
            text,
            count=1,
        )
        if body.lstrip().lower().startswith("with "):
            # Conservative abstention for pre-existing CTE structures; model fallback can handle them.
            continue
        _replace_file(files, path, cte + body, skills, "latest_dimension")


def _required_identifier(files: dict[str, str], context: str, skills: list[str]) -> None:
    match = re.search(rf"`({IDENTIFIER})`\s+is\s+required", context, flags=re.IGNORECASE)
    if not match or "whitespace" not in context.lower() or "must be excluded" not in context.lower():
        return
    identifier = match.group(1)
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or identifier not in text:
            continue
        if re.search(r"\bwhere\b", text, flags=re.IGNORECASE):
            continue
        replacement = text.rstrip() + f"\nwhere nullif(trim(cast({identifier} as varchar)), '') is not null\n"
        _replace_file(files, path, replacement, skills, "required_identifier")


def _categorical_mapping(files: dict[str, str], context: str, skills: list[str]) -> None:
    pairs = re.findall(rf"`?({IDENTIFIER})\s*->\s*({IDENTIFIER})`?", context)
    if len(pairs) < 2:
        return
    outputs = [dst for _, dst in pairs]
    first_source = pairs[0][0]
    for path, text in list(files.items()):
        if path.endswith(".sql"):
            case_match = re.search(
                rf"case\s+.*?when\s+({IDENTIFIER})\s*=\s*['\"]{re.escape(first_source)}['\"].*?end\s+as\s+({IDENTIFIER})",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not case_match:
                continue
            source_field, output_field = case_match.groups()
            lines = ["case"]
            for src, dst in pairs:
                lines.append(f"      when {source_field} = '{src}' then '{dst}'")
            lines.append("      else 'unknown'")
            lines.append(f"    end as {output_field}")
            case_sql = "\n".join(lines)
            replacement = re.sub(
                rf"case\s+.*?end\s+as\s+{re.escape(output_field)}",
                case_sql,
                text,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )
            _replace_file(files, path, replacement, skills, "categorical_mapping")
        elif path.endswith((".yml", ".yaml")) and "accepted_values" in text:
            values = ", ".join(repr(value) for value in outputs)
            replacement = re.sub(r"values:\s*\[[^\]]*\]", f"values: [{values}]", text)
            _replace_file(files, path, replacement, skills, "categorical_mapping")


def _macro_interface(files: dict[str, str], context: str, skills: list[str]) -> None:
    keyword_match = re.search(rf"keyword\s+argument\s+`({IDENTIFIER})`", context, flags=re.IGNORECASE)
    if not keyword_match:
        return
    keyword = keyword_match.group(1)
    value_match = re.search(rf"\b{re.escape(keyword)}\s*=\s*([0-9]+(?:\.[0-9]+)?)", context)
    if not value_match:
        return
    value = value_match.group(1)
    macro_names: list[str] = []
    for path, text in files.items():
        if not path.startswith("macros/"):
            continue
        match = re.search(rf"macro\s+({IDENTIFIER})\([^)]*\b{re.escape(keyword)}\s*=", text, flags=re.IGNORECASE)
        if match:
            macro_names.append(match.group(1))
    if len(macro_names) != 1:
        return
    macro_name = macro_names[0]
    call_re = re.compile(
        rf"(\{{\{{\s*{re.escape(macro_name)}\([^}}]*?)(?:{IDENTIFIER})\s*=\s*{re.escape(value)}([^}}]*\}}\}})"
    )
    for path, text in list(files.items()):
        if not path.endswith(".sql") or path.startswith("macros/"):
            continue
        replacement = call_re.sub(rf"\1{keyword}={value}\2", text)
        _replace_file(files, path, replacement, skills, "macro_interface")


def _latest_record(files: dict[str, str], context: str, skills: list[str]) -> None:
    key_match = re.search(rf"one\s+current\s+row\s+per\s+`({IDENTIFIER})`", context, flags=re.IGNORECASE)
    order_field = _greatest_field(context)
    if not key_match or not order_field:
        return
    key = key_match.group(1)
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or key not in text:
            continue
        if "row_number" in text.lower() or re.search(r"\bqualify\b", text, flags=re.IGNORECASE):
            continue
        replacement = text.rstrip() + (
            "\nqualify row_number() over (\n"
            f"    partition by {key} order by {order_field} desc\n"
            ") = 1\n"
        )
        _replace_file(files, path, replacement, skills, "latest_record")


def _timezone_conversion(files: dict[str, str], context: str, skills: list[str]) -> None:
    zone_match = re.search(r"\b([A-Z][A-Za-z_]+/[A-Z][A-Za-z_]+)\b", context)
    if not zone_match or "source timestamps are utc" not in context.lower():
        return
    zone = zone_match.group(1)
    for path, text in list(files.items()):
        if not path.endswith(".sql"):
            continue
        replacement = re.sub(
            rf"cast\(\s*({IDENTIFIER})\s+as\s+date\s*\)\s+as\s+({IDENTIFIER})",
            rf"cast(timezone('{zone}', timezone('UTC', cast(\1 as timestamp))) as date) as \2",
            text,
            flags=re.IGNORECASE,
        )
        _replace_file(files, path, replacement, skills, "timezone_conversion")


def _business_formula(files: dict[str, str], context: str, skills: list[str]) -> None:
    formula_match = re.search(
        rf"`?({IDENTIFIER})\s*=\s*({IDENTIFIER})\s*-\s*({IDENTIFIER})`?",
        context,
        flags=re.IGNORECASE,
    )
    if not formula_match:
        return
    result_name, positive_term, negative_term = formula_match.groups()
    positive_value = positive_term.lower().rstrip("s")
    negative_value = negative_term.lower().rstrip("s")
    conditional_sum = re.compile(
        rf"sum\s*\(\s*case\s+when\s+({IDENTIFIER})\s*=\s*['\"]([^'\"]+)['\"]\s+then\s+({IDENTIFIER})\s+else\s+0\s+end\s*\)\s+as\s+({IDENTIFIER})",
        flags=re.IGNORECASE,
    )
    for path, text in list(files.items()):
        if not path.endswith(".sql") or result_name not in text:
            continue
        terms = list(conditional_sum.finditer(text))
        positive = next((m for m in terms if m.group(2).lower().rstrip("s") == positive_value), None)
        negative = next((m for m in terms if m.group(2).lower().rstrip("s") == negative_value), None)
        if not positive or not negative:
            continue
        positive_expr = positive.group(0).rsplit(" as ", 1)[0]
        negative_expr = negative.group(0).rsplit(" as ", 1)[0]
        replacement_expr = f"{positive_expr} - {negative_expr} as {result_name}"
        replacement = re.sub(
            rf"sum\s*\(\s*({IDENTIFIER})\s*\)\s+as\s+{re.escape(result_name)}",
            replacement_expr,
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        _replace_file(files, path, replacement, skills, "business_formula")


def propose_contract_patch(root: Path, context: str) -> dict:
    """Create high-confidence repairs from visible contracts and project structure.

    These skills operate only on current project files, source CSV headers, and the
    supplied business context. They deliberately abstain when a rule cannot be
    derived with high confidence so the agent fallback can handle ambiguity.
    """
    root = root.resolve()
    original = _project_files(root)
    files = dict(original)
    headers = _input_headers(root)
    skills: list[str] = []

    _source_alias(files, headers, context, skills)
    _derived_display_name(files, headers, context, skills)
    _safe_numeric(files, context, skills)
    _retarget_missing_refs(root, files, skills)
    _latest_dimension(files, context, skills)
    _required_identifier(files, context, skills)
    _categorical_mapping(files, context, skills)
    _macro_interface(files, context, skills)
    _latest_record(files, context, skills)
    _timezone_conversion(files, context, skills)
    _business_formula(files, context, skills)

    changed = [
        {"path": path, "content": content}
        for path, content in sorted(files.items())
        if original.get(path) != content
    ]
    root_causes = [SKILL_ROOT_CAUSE[name] for name in skills if name in SKILL_ROOT_CAUSE]
    unique_root_causes = list(dict.fromkeys(root_causes))
    if len(unique_root_causes) > 1:
        predicted = "multi_fault_schema_and_type_drift"
    elif unique_root_causes:
        predicted = unique_root_causes[0]
    else:
        predicted = "unknown"

    return {
        "explanation": "Applied high-confidence repair skills derived from visible project structure and documented business contracts.",
        "files": changed,
        "skills": skills,
        "root_cause_class": predicted,
    }
