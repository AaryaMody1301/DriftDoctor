from __future__ import annotations

from pathlib import Path


PUBLIC_CONTEXT: dict[str, str] = {
    "DD-001": """# Business context\n\nThe public mart contract is `customer_id`, `customer_name`, `revenue_amount`. Upstream renamed the human-readable customer field, but downstream names must remain stable.\n""",
    "DD-002": """# Business context\n\nThe public customer model must expose `customer_id`, `display_name`, and `revenue_amount`. `display_name` is the trimmed concatenation of `first_name`, a single space, and `last_name`.\n""",
    "DD-003": """# Business context\n\n`amount` is numeric downstream. Source text that is valid numeric data should be converted to DECIMAL. Invalid numeric text must become NULL rather than be coerced to zero or dropped.\n""",
    "DD-004": """# Business context\n\nThe mart contract remains `order_id`, `customer_id`, `amount`. The staging model was renamed during the refactor; use the current staging model rather than recreating the removed name.\n""",
    "DD-005": """# Business context\n\nThe finance fact grain is one row per `order_id`. Customer tier is a slowly changing attribute; when multiple tier records exist, use the record with the greatest `effective_at` for that customer. Revenue must never be multiplied by dimension history.\n""",
    "DD-006": """# Business context\n\n`customer_id` is required. Source rows with NULL, empty, or whitespace-only customer IDs are invalid and must be excluded; do not invent replacement identifiers.\n""",
    "DD-007": """# Business context\n\nBusiness status mapping is: `paid -> revenue`, `refunded -> refund`, `chargeback -> loss`. Validation must explicitly allow exactly the mapped business statuses rather than being removed.\n""",
    "DD-008": """# Business context\n\nThe shared currency macro now accepts a required expression plus keyword argument `scale`. Payment cents should be normalized to dollars with `scale=100`. Do not change the macro back to its old interface.\n""",
    "DD-009": """# Business context\n\nThe model contract is exactly one current row per `customer_id`. If multiple records exist, choose the row with the greatest `updated_at`.\n""",
    "DD-010": """# Business context\n\nReporting dates use Asia/Kolkata local calendar dates. Source timestamps are UTC. Convert from UTC to Asia/Kolkata before casting to DATE.\n""",
    "DD-011": """# Business context\n\nSource refund amounts are stored as positive magnitudes. `gross_sales` is the sum of sales, `refunds` is the positive refund magnitude, and `net_revenue = sales - refunds`.\n""",
    "DD-012": """# Business context\n\nThe public mart contract is `customer_id`, `customer_name`, `revenue_amount`. The upstream name field may have changed. Revenue now arrives as text: valid numeric text becomes DECIMAL and invalid text becomes NULL; invalid values must not be silently coerced to zero or discarded.\n""",
}


def write_public_context(case_id: str, workdir: Path) -> None:
    try:
        content = PUBLIC_CONTEXT[case_id]
    except KeyError as exc:
        raise ValueError(f"Unknown case: {case_id}") from exc
    (workdir / "BUSINESS_CONTEXT.md").write_text(content, encoding="utf-8")
