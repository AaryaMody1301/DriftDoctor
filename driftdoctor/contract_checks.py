from __future__ import annotations

import csv
import re
from pathlib import Path

IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


def _project_text(root: Path) -> str:
    parts: list[str] = []
    for pattern in ("models/**/*.sql", "models/**/*.yml", "models/**/*.yaml", "macros/**/*.sql"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts).lower()


def _schema_text(root: Path) -> str:
    parts: list[str] = []
    for pattern in ("models/**/*.yml", "models/**/*.yaml"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts).lower()


def _input_headers(root: Path) -> set[str]:
    headers: set[str] = set()
    for path in sorted((root / "input").glob("*.csv")):
        with path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle)
            try:
                headers.update(cell.strip().lower() for cell in next(reader))
            except StopIteration:
                pass
    return headers


def _quoted_identifiers(text: str) -> list[str]:
    return re.findall(rf"`({IDENTIFIER})`", text)


def _declared_contract_fields(context: str) -> list[str]:
    """Return only explicit public output-field declarations, not grain clauses."""
    fields: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", context):
        lower = sentence.lower()
        declares_public_fields = ("public" in lower and "contract" in lower) or "must expose" in lower
        if not declares_public_fields:
            continue
        for identifier in _quoted_identifiers(sentence):
            lowered = identifier.lower()
            if lowered not in fields:
                fields.append(lowered)
    return fields


def _derived_rules(context: str) -> list[tuple[str, str, str]]:
    return [
        (match.group("out").lower(), match.group("first").lower(), match.group("last").lower())
        for match in re.finditer(
            rf"`(?P<out>{IDENTIFIER})`\s+is\s+the\s+trimmed\s+concatenation\s+of\s+`(?P<first>{IDENTIFIER})`.*?`(?P<last>{IDENTIFIER})`",
            context,
            flags=re.IGNORECASE | re.DOTALL,
        )
    ]


def _mapping_pairs(context: str) -> list[tuple[str, str]]:
    return [(src.lower(), dst.lower()) for src, dst in re.findall(rf"`?({IDENTIFIER})\s*->\s*({IDENTIFIER})`?", context)]


def _formula(context: str) -> tuple[str, str, str] | None:
    match = re.search(
        rf"`?({IDENTIFIER})\s*=\s*({IDENTIFIER})\s*-\s*({IDENTIFIER})`?",
        context,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return tuple(part.lower() for part in match.groups())  # type: ignore[return-value]


def _iana_zone(context: str) -> str | None:
    match = re.search(r"\b([A-Z][A-Za-z_]+/[A-Z][A-Za-z_]+)\b", context)
    return match.group(1).lower() if match else None


def semantic_concerns(root: Path, context: str) -> list[str]:
    """Check visible business contracts without benchmark-specific names or oracles.

    These checks intentionally cover only rules that can be parsed from the supplied
    BUSINESS_CONTEXT. They are conservative: if a rule is not stated explicitly, the
    verifier does not invent one. A clean result is supporting evidence, not a substitute
    for project-specific tests or human approval.
    """
    root = root.resolve()
    ctx = context.lower()
    code = _project_text(root)
    schema = _schema_text(root)
    headers = _input_headers(root)
    concerns: list[str] = []

    if "numeric" in ctx and "invalid" in ctx and "null" in ctx and "try_cast" not in code:
        concerns.append("Documented invalid-numeric-to-NULL handling is not visible in current SQL.")

    derived_outputs: set[str] = set()
    for output, first, last in _derived_rules(context):
        derived_outputs.add(output)
        alias = re.search(rf"\bas\s+{re.escape(output)}\b", code)
        if "trim(" not in code or first not in code or last not in code or alias is None:
            concerns.append(
                f"Documented derived field {output} is not visibly produced from {first} and {last} with trimming."
            )

    required_match = re.search(rf"`({IDENTIFIER})`\s+is\s+required", context, flags=re.IGNORECASE)
    if required_match and "whitespace" in ctx and "must be excluded" in ctx:
        identifier = required_match.group(1).lower()
        has_trim = re.search(rf"trim\s*\([^)]*\b{re.escape(identifier)}\b", code) is not None
        has_rejection = "nullif(" in code or "<> ''" in code or "!= ''" in code
        if not (has_trim and has_rejection):
            concerns.append(f"Required identifier {identifier} is not visibly filtering NULL/blank/whitespace rows.")

    pairs = _mapping_pairs(context)
    if len(pairs) >= 2:
        for src, dst in pairs:
            if src not in code or dst not in code:
                concerns.append(f"Documented categorical mapping {src} -> {dst} is not visible in project logic.")
        if "accepted_values" in schema:
            missing = sorted({dst for _, dst in pairs if dst not in schema})
            if missing:
                concerns.append("accepted_values validation is missing documented outputs: " + ", ".join(missing))

    keyword_match = re.search(rf"keyword\s+argument\s+`({IDENTIFIER})`", context, flags=re.IGNORECASE)
    if keyword_match:
        keyword = keyword_match.group(1).lower()
        value_match = re.search(rf"\b{re.escape(keyword)}\s*=\s*([0-9]+(?:\.[0-9]+)?)", context, flags=re.IGNORECASE)
        if value_match and re.search(rf"\b{re.escape(keyword)}\s*=\s*{re.escape(value_match.group(1))}\b", code) is None:
            concerns.append(f"Documented macro keyword {keyword}={value_match.group(1)} is not visible at a call site.")

    greatest = re.search(rf"greatest\s+`({IDENTIFIER})`", context, flags=re.IGNORECASE)
    if greatest:
        order_field = greatest.group(1).lower()
        needs_latest = "one current row per" in ctx or "slowly changing" in ctx or "multiple records" in ctx
        latest_operator = any(token in code for token in ("row_number", "arg_max", "max_by"))
        if needs_latest and (order_field not in code or not latest_operator):
            concerns.append(f"Documented greatest-{order_field} record selection is not visible in current SQL.")

    zone = _iana_zone(context)
    if zone and "source timestamps are utc" in ctx:
        has_zone = zone in code
        has_utc = "timezone('utc'" in code or 'timezone("utc"' in code or "at time zone 'utc'" in code
        if not (has_zone and has_utc):
            concerns.append(f"Documented UTC-to-{zone} conversion is not visible before reporting-date logic.")

    formula = _formula(context)
    if formula:
        result, positive, negative = formula
        expression = re.search(rf"([^\n,]+)\bas\s+{re.escape(result)}\b", code)
        if expression is None or "-" not in expression.group(1):
            concerns.append(f"Documented formula {result} = {positive} - {negative} is not visible in the output expression.")

    for field in _declared_contract_fields(context):
        if field in headers or field in derived_outputs:
            continue
        if re.search(rf"\bas\s+{re.escape(field)}\b", code) is None:
            concerns.append(f"Public contract field {field} is absent from source headers and lacks a visible alias/derivation.")

    return list(dict.fromkeys(concerns))
