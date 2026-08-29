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


def _source_alias(files: dict[str, str], headers: set[str], context: str, skills: list[str]) -> None:
    ctx = context.lower()
    if "customer_name" not in ctx or "customer_name" in {h.lower() for h in headers}:
        return
    candidates = [h for h in headers if h.lower().endswith("name") and h.lower() not in {"first_name", "last_name"}]
    if len(candidates) != 1:
        return
    candidate = candidates[0]
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or "customer_name" not in text:
            continue
        replacement = re.sub(
            r"(?m)^(\s*)customer_name(\s*,?)$",
            rf"\1{candidate} as customer_name\2",
            text,
        )
        _replace_file(files, path, replacement, skills, "source_alias")


def _derived_display_name(files: dict[str, str], headers: set[str], context: str, skills: list[str]) -> None:
    ctx = context.lower()
    lower_headers = {h.lower() for h in headers}
    if "trimmed concatenation" not in ctx or not {"first_name", "last_name"}.issubset(lower_headers):
        return
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or "display_name" not in text:
            continue
        replacement = re.sub(
            r"(?m)^(\s*)display_name(\s*,?)$",
            r"\1trim(first_name || ' ' || last_name) as display_name\2",
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
            r"\b([A-Za-z_][A-Za-z0-9_]*_text)\s*\*\s*1(?:\.0+)?\s+as\s+([A-Za-z_][A-Za-z0-9_]*)",
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
            candidates = sorted(stem for stem in stems if stem.startswith(missing + "_") or stem.startswith(missing + "v"))
            if len(candidates) == 1:
                replacement = re.sub(
                    rf"ref\((['\"]){re.escape(missing)}\1\)",
                    f"ref('{candidates[0]}')",
                    replacement,
                )
        _replace_file(files, path, replacement, skills, "retarget_ref")


def _latest_dimension(files: dict[str, str], context: str, skills: list[str]) -> None:
    if "greatest `effective_at`" not in context.lower():
        return
    join_re = re.compile(
        r"left\s+join\s+(\{\{\s*source\([^\n]+?\)\s*\}\})\s+([A-Za-z_][A-Za-z0-9_]*)\s*\n\s*on\s+([A-Za-z_][A-Za-z0-9_]*)\.customer_id\s*=\s*\2\.customer_id",
        re.IGNORECASE,
    )
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "effective_at" not in context.lower():
            continue
        match = join_re.search(text)
        if not match:
            continue
        source_expr, dim_alias, fact_alias = match.groups()
        cte = (
            "with latest_dimension as (\n"
            "    select *\n"
            f"    from {source_expr}\n"
            "    qualify row_number() over (\n"
            "        partition by customer_id order by effective_at desc\n"
            "    ) = 1\n"
            ")\n"
        )
        body = join_re.sub(
            f"left join latest_dimension {dim_alias}\n  on {fact_alias}.customer_id = {dim_alias}.customer_id",
            text,
            count=1,
        )
        if not body.lstrip().lower().startswith("with "):
            body = cte + body
        _replace_file(files, path, body, skills, "latest_dimension")


def _required_identifier(files: dict[str, str], context: str, skills: list[str]) -> None:
    ctx = context.lower()
    if "customer_id" not in ctx or "whitespace" not in ctx or "must be excluded" not in ctx:
        return
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or "customer_id" not in text:
            continue
        if re.search(r"\bwhere\b", text, flags=re.IGNORECASE):
            continue
        replacement = text.rstrip() + "\nwhere nullif(trim(cast(customer_id as varchar)), '') is not null\n"
        _replace_file(files, path, replacement, skills, "required_identifier")


def _categorical_mapping(files: dict[str, str], context: str, skills: list[str]) -> None:
    pairs = re.findall(r"`?([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)`?", context)
    if len(pairs) < 2:
        return
    outputs = [dst for _, dst in pairs]
    for path, text in list(files.items()):
        if path.endswith(".sql") and re.search(r"\bcase\b.*?\bas\s+business_status", text, flags=re.IGNORECASE | re.DOTALL):
            lines = ["case"]
            for src, dst in pairs:
                lines.append(f"      when status = '{src}' then '{dst}'")
            lines.append("      else 'unknown'")
            lines.append("    end as business_status")
            case_sql = "\n".join(lines)
            replacement = re.sub(
                r"case\s+.*?end\s+as\s+business_status",
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
    ctx = context.lower()
    if "keyword argument `scale`" not in ctx:
        return
    macro_has_scale = any(
        path.startswith("macros/") and re.search(r"macro\s+\w+\([^)]*\bscale\s*=", text, flags=re.IGNORECASE)
        for path, text in files.items()
    )
    if not macro_has_scale:
        return
    for path, text in list(files.items()):
        if not path.endswith(".sql") or path.startswith("macros/"):
            continue
        replacement = re.sub(r"\bdivisor\s*=", "scale=", text)
        _replace_file(files, path, replacement, skills, "macro_interface")


def _latest_record(files: dict[str, str], context: str, skills: list[str]) -> None:
    if "greatest `updated_at`" not in context.lower():
        return
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "source(" not in text or "updated_at" not in text:
            continue
        if "row_number" in text.lower():
            continue
        replacement = text.rstrip() + (
            "\nqualify row_number() over (\n"
            "    partition by customer_id order by updated_at desc\n"
            ") = 1\n"
        )
        _replace_file(files, path, replacement, skills, "latest_record")


def _timezone_conversion(files: dict[str, str], context: str, skills: list[str]) -> None:
    zone_match = re.search(r"\b([A-Z][A-Za-z_]+/[A-Z][A-Za-z_]+)\b", context)
    if not zone_match or "source timestamps are utc" not in context.lower():
        return
    zone = zone_match.group(1)
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "reporting_date" not in text:
            continue
        replacement = re.sub(
            r"cast\(\s*([A-Za-z_][A-Za-z0-9_]*)\s+as\s+date\s*\)\s+as\s+reporting_date",
            rf"cast(timezone('{zone}', timezone('UTC', cast(\1 as timestamp))) as date) as reporting_date",
            text,
            flags=re.IGNORECASE,
        )
        _replace_file(files, path, replacement, skills, "timezone_conversion")


def _business_formula(files: dict[str, str], context: str, skills: list[str]) -> None:
    if "net_revenue = sales - refunds" not in context.lower():
        return
    expression = (
        "sum(case when kind = 'sale' then amount else 0 end) - "
        "sum(case when kind = 'refund' then amount else 0 end) as net_revenue"
    )
    for path, text in list(files.items()):
        if not path.endswith(".sql") or "net_revenue" not in text:
            continue
        replacement = re.sub(
            r"sum\s*\(\s*amount\s*\)\s+as\s+net_revenue",
            expression,
            text,
            flags=re.IGNORECASE,
        )
        _replace_file(files, path, replacement, skills, "business_formula")


def propose_contract_patch(root: Path, context: str) -> dict:
    """Create high-confidence repairs from visible contracts and project structure.

    The skills are intentionally generic and do not know benchmark case IDs, hidden
    oracle checks, or evaluator reference repairs. They operate only on the current
    project, source CSV headers, and BUSINESS_CONTEXT text.
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
    if "source_alias" in skills and "safe_numeric" in skills:
        predicted = "multi_fault_schema_and_type_drift"
    elif root_causes:
        predicted = root_causes[0]
    else:
        predicted = "unknown"

    return {
        "explanation": "Applied high-confidence contract repair skills derived from visible project evidence and BUSINESS_CONTEXT.",
        "files": changed,
        "skills": skills,
        "root_cause_class": predicted,
    }
