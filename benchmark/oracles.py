"""External deterministic evaluator for DriftDoctor benchmark cases."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class EvaluationResult:
    case_id: str
    passed: bool
    checks: list[Check]
    dbt_returncode: int
    dbt_stdout: str
    dbt_stderr: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [asdict(c) for c in self.checks]
        return payload


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _rows(con: Any, sql: str) -> list[list[Any]]:
    return [[_normalize(v) for v in row] for row in con.execute(sql).fetchall()]


def _check_rows(con: Any, name: str, sql: str, expected: list[list[Any]]) -> Check:
    try:
        actual = _rows(con, sql)
        return Check(name, actual == expected, f"expected={expected!r}; actual={actual!r}")
    except Exception as exc:
        return Check(name, False, f"query error: {exc}")


def _check_scalar(con: Any, name: str, sql: str, expected: Any) -> Check:
    try:
        row = con.execute(sql).fetchone()
        actual = _normalize(row[0]) if row else None
        return Check(name, actual == expected, f"expected={expected!r}; actual={actual!r}")
    except Exception as exc:
        return Check(name, False, f"query error: {exc}")


def _check_file(name: str, path: Path, predicate: Callable[[str], bool], detail: str) -> Check:
    try:
        text = path.read_text(encoding="utf-8")
        return Check(name, predicate(text), detail)
    except Exception as exc:
        return Check(name, False, f"file error: {exc}")


def _table_columns(con: Any, schema: str, table: str) -> list[str]:
    rows = con.execute(
        "select column_name from information_schema.columns "
        "where table_schema = ? and table_name = ? order by ordinal_position",
        [schema, table],
    ).fetchall()
    return [row[0] for row in rows]


def _case_checks(case_id: str, workdir: Path, con: Any) -> list[Check]:
    checks: list[Check] = []

    if case_id == "DD-001":
        try:
            cols = _table_columns(con, "analytics", "mart_customer_revenue")
            checks.append(Check("downstream_contract_preserved", cols == ["customer_id", "customer_name", "revenue_amount"], repr(cols)))
        except Exception as exc:
            checks.append(Check("downstream_contract_preserved", False, str(exc)))
        checks.append(_check_rows(
            con,
            "renamed_source_field_regression",
            "select customer_id, customer_name, revenue_amount from analytics.mart_customer_revenue order by customer_id",
            [[1, "Ada Lovelace", 100], [2, "Grace Hopper", 250]],
        ))

    elif case_id == "DD-002":
        checks.append(_check_rows(
            con,
            "derived_display_name_business_invariant",
            "select customer_id, display_name, revenue_amount from analytics.mart_customers order by customer_id",
            [[1, "Ada Lovelace", 100], [2, "Grace Hopper", 250]],
        ))
        checks.append(_check_scalar(con, "row_count_preserved", "select count(*) from analytics.mart_customers", 2))

    elif case_id == "DD-003":
        checks.append(_check_rows(
            con,
            "safe_numeric_conversion",
            "select order_id, amount from analytics.stg_orders order by order_id",
            [[1, 100.5], [2, None], [3, 25.0]],
        ))
        checks.append(_check_scalar(con, "invalid_numeric_is_not_silently_coerced", "select count(*) from analytics.stg_orders where order_id = 2 and amount is null", 1))

    elif case_id == "DD-004":
        checks.append(_check_rows(
            con,
            "renamed_ref_output_contract",
            "select order_id, customer_id, amount from analytics.mart_orders order by order_id",
            [[1, 10, 100], [2, 20, 50]],
        ))
        checks.append(_check_file(
            "no_stale_ref",
            workdir / "models/mart_orders.sql",
            lambda text: "ref('stg_orders')" not in text and 'ref("stg_orders")' not in text,
            "old model ref must not remain",
        ))

    elif case_id == "DD-005":
        checks.append(_check_scalar(con, "fact_grain_unique", "select count(*) - count(distinct order_id) from analytics.fct_revenue", 0))
        checks.append(_check_scalar(con, "frozen_total_revenue", "select sum(revenue) from analytics.fct_revenue", 300))
        checks.append(_check_rows(
            con,
            "latest_dimension_value_selected",
            "select order_id, customer_id, tier, revenue from analytics.fct_revenue order by order_id",
            [[1, 10, "gold", 100], [2, 20, "silver", 200]],
        ))

    elif case_id == "DD-006":
        checks.append(_check_scalar(con, "required_identifier_not_null", "select count(*) from analytics.stg_customers where customer_id is null or trim(customer_id) = ''", 0))
        checks.append(_check_scalar(con, "frozen_row_count", "select count(*) from analytics.stg_customers", 2))
        checks.append(_check_rows(
            con,
            "no_invented_identifiers",
            "select customer_id from analytics.stg_customers order by customer_id",
            [["C001"], ["C003"]],
        ))

    elif case_id == "DD-007":
        checks.append(_check_rows(
            con,
            "new_category_mapping",
            "select order_id, status, business_status from analytics.stg_order_status order by order_id",
            [[1, "paid", "revenue"], [2, "refunded", "refund"], [3, "chargeback", "loss"]],
        ))
        checks.append(_check_file(
            "accepted_values_validation_remains_explicit",
            workdir / "models/schema.yml",
            lambda text: "accepted_values" in text and "loss" in text,
            "schema.yml must retain accepted_values and include loss",
        ))

    elif case_id == "DD-008":
        checks.append(_check_rows(
            con,
            "macro_output_matches_fixture",
            "select payment_id, amount_dollars from analytics.stg_payments order by payment_id",
            [[1, 12.34], [2, 50.0]],
        ))
        checks.append(_check_file(
            "macro_call_uses_current_interface",
            workdir / "models/stg_payments.sql",
            lambda text: "divisor=" not in text and "scale=" in text,
            "call site must use the current scale argument",
        ))

    elif case_id == "DD-009":
        checks.append(_check_scalar(con, "customer_grain_unique", "select count(*) - count(distinct customer_id) from analytics.current_customers", 0))
        checks.append(_check_rows(
            con,
            "recency_rule_preserved",
            "select customer_id, email from analytics.current_customers order by customer_id",
            [["C001", "new@example.com"], ["C002", "stable@example.com"]],
        ))

    elif case_id == "DD-010":
        checks.append(_check_rows(
            con,
            "reporting_timezone_boundaries",
            "select event_id, reporting_date, amount from analytics.daily_events order by event_id",
            [[1, "2026-08-28", 10], [2, "2026-08-29", 20], [3, "2026-08-29", 30]],
        ))
        checks.append(_check_rows(
            con,
            "daily_aggregate_totals",
            "select reporting_date, sum(amount) from analytics.daily_events group by reporting_date order by reporting_date",
            [["2026-08-28", 10], ["2026-08-29", 50]],
        ))

    elif case_id == "DD-011":
        checks.append(_check_rows(
            con,
            "accounting_rule",
            "select gross_sales, refunds, net_revenue from analytics.revenue_summary",
            [[150, 20, 130]],
        ))

    elif case_id == "DD-012":
        checks.append(_check_rows(
            con,
            "multi_fault_output_contract",
            "select customer_id, customer_name, revenue_amount from analytics.mart_customer_revenue order by customer_id",
            [[1, "Ada", 100.0], [2, "Grace", None], [3, "Linus", 50.0]],
        ))
        checks.append(_check_scalar(con, "invalid_source_value_handled_explicitly", "select count(*) from analytics.mart_customer_revenue where customer_id = 2 and revenue_amount is null", 1))

    else:
        checks.append(Check("known_case", False, f"unknown case {case_id}"))

    return checks


def evaluate_case(case_id: str, workdir: Path, timeout_seconds: int = 120) -> EvaluationResult:
    workdir = workdir.resolve()
    marker = workdir / ".driftdoctor-case"
    if not marker.exists() or marker.read_text(encoding="utf-8").strip() != case_id:
        raise ValueError(f"{workdir} is not a materialized {case_id} workspace")

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    try:
        proc = subprocess.run(
            ["dbt", "build", "--project-dir", str(workdir), "--profiles-dir", str(workdir)],
            cwd=workdir,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        returncode = proc.returncode
        stdout = proc.stdout[-20000:]
        stderr = proc.stderr[-20000:]
    except subprocess.TimeoutExpired as exc:
        return EvaluationResult(
            case_id=case_id,
            passed=False,
            checks=[Check("dbt_build_succeeds", False, f"timeout after {timeout_seconds}s")],
            dbt_returncode=124,
            dbt_stdout=(exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            dbt_stderr=(exc.stderr or "")[-20000:] if isinstance(exc.stderr, str) else "",
        )

    checks = [Check("dbt_build_succeeds", returncode == 0, f"returncode={returncode}")]

    try:
        import duckdb

        con = duckdb.connect(str(workdir / "benchmark.duckdb"), read_only=True)
        try:
            checks.extend(_case_checks(case_id, workdir, con))
        finally:
            con.close()
    except Exception as exc:
        checks.append(Check("oracle_database_access", False, str(exc)))

    passed = all(check.passed for check in checks)
    return EvaluationResult(case_id, passed, checks, returncode, stdout, stderr)


def dump_result(result: EvaluationResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
