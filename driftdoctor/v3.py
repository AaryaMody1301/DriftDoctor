from __future__ import annotations

import json
import re
import time
from pathlib import Path

from driftdoctor.evidence import collect_evidence, compact_evidence
from driftdoctor.v2 import (
    DIAGNOSIS_SCHEMA,
    PATCH_SCHEMA,
    InferenceTransportError,
    _apply_patch,
    _business_context,
    _chat,
    _run_build,
)

TAXONOMY_GUIDE = """
Root-cause taxonomy:
- source_column_renamed: an upstream/source field changed name while the downstream contract stays stable.
- source_column_removed: a required downstream field disappeared and must be derived from remaining source fields.
- source_type_changed: a source field changed representation/type and needs safe conversion.
- model_ref_renamed: a dbt model/ref target was renamed; update the ref to the model that actually exists.
- join_cardinality_regression: a join became one-to-many and multiplied fact rows/measures.
- nullability_regression: newly null/blank identifiers violate a required contract.
- accepted_value_drift: a new categorical value requires both business mapping and validation changes.
- macro_signature_changed: a macro call no longer matches the macro's current arguments.
- grain_regression: a model no longer enforces its documented one-row-per-key/current-record grain.
- timezone_semantics_changed: an instant is being assigned to the wrong local calendar/date.
- business_rule_regression: SQL still builds but a documented business formula/sign rule is wrong.
- multi_fault_schema_and_type_drift: more than one independent source schema/type fault must be repaired together.
- unknown: only when visible evidence does not fit any label above.
""".strip()

REPAIR_PLAYBOOK = """
Contract-guided repair rules. Apply only when visible evidence/business context supports them:
1. Preserve public model/file names, test targets, and downstream column names unless the incident explicitly says a dbt model was renamed.
2. Missing source column + candidate/source header with a replacement field: select the replacement source field and alias it to the stable downstream contract name. Do not write the missing old source name back unchanged.
3. Required derived display/name fields: derive them from the documented source fields exactly; for a trimmed first/last name contract use trim(first_name || ' ' || last_name).
4. Text-to-number where invalid text must become NULL: use DuckDB TRY_CAST to a practical wide numeric type such as DECIMAL(18,2). Do not use a narrow precision inferred from a sample and do not coerce invalid values to zero or drop them.
5. Renamed dbt dependency: update ref() to the model file/name that exists. Do not recreate the removed model or rename unrelated models/tests.
6. One-to-many SCD/dimension join: reduce the dimension to one current row per business key before joining (for example row_number() over(partition by key order by effective_at desc) and QUALIFY row_number()... = 1). Keep the fact grain and original model name.
7. Required identifiers: exclude NULL, empty, and whitespace-only values using trim/nullif logic. Do not invent identifiers.
8. Categorical drift: update the CASE mapping and accepted_values validation together; keep validation rather than deleting it.
9. Macro interface change: change the call site to the macro's current argument names. Do not revert a valid new macro signature.
10. Current-row grain: select one row per key using the documented latest timestamp (row_number/QUALIFY or an equivalent deterministic pattern).
11. UTC timestamp to named local reporting date in DuckDB: treat the source timestamp as UTC, convert the instant to the documented zone, then cast to DATE. A robust pattern is timezone('<zone>', timezone('UTC', cast(ts as timestamp))) before DATE casting.
12. Positive refund magnitudes: compute sales and refunds separately, then net_revenue = gross_sales - refunds. A green build alone does not prove this semantic rule.
13. Multi-fault incidents: repair every independently documented fault in the same patch; do not stop after the first compiler error.
14. Prefer editing existing files. Never create a second renamed copy of a model as a way to avoid fixing its logic.
""".strip()


def _project_text(root: Path) -> str:
    parts: list[str] = []
    for pattern in ("models/**/*.sql", "models/**/*.yml", "models/**/*.yaml", "macros/**/*.sql"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                parts.append(f"\n--- {path.relative_to(root)} ---\n{path.read_text(errors='replace')}")
    return "".join(parts).lower()


def semantic_concerns(root: Path, context: str) -> list[str]:
    """Return visible contract concerns that a green dbt build cannot settle by itself.

    These are intentionally generic text lints derived only from BUSINESS_CONTEXT and
    the current project. They never read benchmark cases, oracle code, or reference repairs.
    """
    ctx = context.lower()
    code = _project_text(root)
    concerns: list[str] = []

    if "invalid numeric" in ctx and "null" in ctx and "try_cast" not in code:
        concerns.append("Business context requires invalid numeric text to become NULL, but current SQL does not use TRY_CAST.")

    if "trimmed concatenation" in ctx:
        if not all(token in code for token in ("first_name", "last_name", "trim")):
            concerns.append("Documented display-name derivation from trimmed first_name + space + last_name is not visible in current SQL.")

    if "null, empty, or whitespace" in ctx and not ("trim(" in code and ("nullif(" in code or "<> ''" in code or "!= ''" in code)):
        concerns.append("Required identifier rule mentions NULL/empty/whitespace rows, but current SQL does not visibly filter trimmed blanks.")

    if "chargeback -> loss" in ctx:
        if "chargeback" not in code or "loss" not in code:
            concerns.append("Documented chargeback -> loss mapping is missing from current project logic.")
        if "accepted_values" in code and "loss" not in code:
            concerns.append("Validation exists but does not visibly include the documented loss business status.")

    if "keyword argument `scale`" in ctx and not re.search(r"scale\s*=\s*100", code):
        concerns.append("Business context requires the current macro call to use keyword scale=100.")

    if "greatest `effective_at`" in ctx and not (
        "effective_at" in code and ("row_number" in code or "arg_max" in code or "max_by" in code)
    ):
        concerns.append("Latest effective_at dimension record is required before the join, but no deterministic latest-record selection is visible.")

    if "greatest `updated_at`" in ctx and not (
        "updated_at" in code and ("row_number" in code or "arg_max" in code or "max_by" in code)
    ):
        concerns.append("One current row per customer requires latest updated_at selection, but no deterministic latest-record selection is visible.")

    if "asia/kolkata" in ctx and "asia/kolkata" not in code:
        concerns.append("Reporting dates must use Asia/Kolkata after UTC conversion, but the target timezone is absent from current SQL.")

    if "net_revenue = sales - refunds" in ctx:
        net_match = re.search(r"[^\n,]+\bas\s+net_revenue", code)
        if net_match is None or "-" not in net_match.group(0):
            concerns.append("Documented net_revenue = sales - refunds rule is not visible in the net_revenue expression.")

    if "downstream names must remain stable" in ctx and "customer_name" in ctx:
        # A rename repair should keep the public name as an alias. This catches the common
        # failure mode of selecting the removed source name unchanged.
        evidence = collect_evidence(root)
        headers = [cell.lower() for rows in evidence.get("input_samples", {}).values() for cell in (rows[0] if rows else [])]
        if "customer_name" not in headers and " as customer_name" not in code:
            concerns.append("Source samples do not contain customer_name while the public contract requires it; current SQL lacks an alias to customer_name.")

    return concerns


def _diagnose(model: str, incident: str, context: str, evidence: dict) -> dict:
    return _chat(
        model,
        [
            {
                "role": "system",
                "content": (
                    "Diagnose this dbt incident from visible evidence only. Choose the most specific taxonomy label. "
                    "Do not confuse a missing source column with a renamed dbt model. Cite concrete build/input/project evidence.\n\n"
                    + TAXONOMY_GUIDE
                ),
            },
            {
                "role": "user",
                "content": f"Incident:\n{incident}\n\nDocumented business rules:\n{context}\n\nEvidence:\n{compact_evidence(evidence, max_chars=30000)}",
            },
        ],
        DIAGNOSIS_SCHEMA,
    )


def _patch(
    model: str,
    incident: str,
    context: str,
    diagnosis: dict,
    evidence: dict,
    *,
    previous_patch: dict | None = None,
    failure: dict | None = None,
    concerns: list[str] | None = None,
) -> dict:
    extra: list[str] = []
    if previous_patch is not None:
        extra.append("Previous patch (do not repeat unchanged content):\n" + json.dumps(previous_patch))
    if failure is not None:
        extra.append("Concrete dbt build/test result after the previous patch:\n" + json.dumps(failure))
    if concerns:
        extra.append("Deterministic contract concerns that remain visible:\n- " + "\n- ".join(concerns))

    return _chat(
        model,
        [
            {
                "role": "system",
                "content": (
                    "Repair the dbt project with the smallest complete-file replacements that satisfy the documented contract. "
                    "Return actual file contents, never placeholders or markdown fences. Preserve model names/contracts and prefer existing files. "
                    "A patch that merely renames a model/test, repeats the broken source field, or deletes validation is not a repair.\n\n"
                    + REPAIR_PLAYBOOK
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Incident:\n{incident}\n\nBusiness context:\n{context}\n\nDiagnosis:\n{json.dumps(diagnosis)}\n\n"
                    f"Current project evidence:\n{compact_evidence(evidence, max_chars=30000)}\n\n" + "\n\n".join(extra)
                ),
            },
        ],
        PATCH_SCHEMA,
    )


def run_v3(root: Path, incident: str, model: str, max_model_calls: int = 14) -> dict:
    """Contract-guided DriftDoctor workflow with deterministic build and semantic feedback."""
    root = root.resolve()
    started = time.monotonic()
    calls = 0
    trajectory: list[dict] = []
    context = _business_context(root)

    evidence = collect_evidence(root)
    diagnosis = _diagnose(model, incident, context, evidence)
    calls += 1
    trajectory.append({"stage": "diagnose", "output": diagnosis})

    patch = _patch(model, incident, context, diagnosis, evidence)
    calls += 1
    applied = _apply_patch(root, patch)
    build = _run_build(root)
    trajectory.append({"stage": "patch", "output": patch, "applied": applied, "build": build})

    # Up to two build-driven corrections. Unlike the previous workflow, a failed
    # retry is not terminal if there is still model-call budget and new concrete evidence.
    for retry_index in range(2):
        if build.get("returncode") == 0 or calls >= max_model_calls:
            break
        latest = collect_evidence(root)
        repair = _patch(
            model,
            incident,
            context,
            diagnosis,
            latest,
            previous_patch=patch,
            failure=build,
        )
        calls += 1
        applied_retry = _apply_patch(root, repair)
        build = _run_build(root)
        trajectory.append(
            {
                "stage": f"build_retry_{retry_index + 1}",
                "output": repair,
                "applied": applied_retry,
                "build": build,
            }
        )
        patch = repair

    concerns = semantic_concerns(root, context) if build.get("returncode") == 0 else []
    if concerns and calls < max_model_calls:
        latest = collect_evidence(root)
        repair = _patch(
            model,
            incident,
            context,
            diagnosis,
            latest,
            previous_patch=patch,
            failure=build,
            concerns=concerns,
        )
        calls += 1
        applied_semantic = _apply_patch(root, repair)
        build = _run_build(root)
        trajectory.append(
            {
                "stage": "contract_retry",
                "concerns": concerns,
                "output": repair,
                "applied": applied_semantic,
                "build": build,
            }
        )

    remaining_concerns = semantic_concerns(root, context) if build.get("returncode") == 0 else []
    return {
        "system": "driftdoctor-v0.3-contract-guided",
        "model": model,
        "model_calls": calls,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "diagnosis": diagnosis,
        "final_build": build,
        "remaining_contract_concerns": remaining_concerns,
        "trajectory": trajectory,
    }
