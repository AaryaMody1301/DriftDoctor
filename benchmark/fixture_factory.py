"""Synthetic dbt + DuckDB benchmark fixtures for DriftDoctor.

The agent receives only the materialized case directory. Evaluator-only code lives
outside that directory and is not required to solve a case.
"""
from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Callable

PROJECT_YML = """name: driftdoctor_case
version: '1.0.0'
config-version: 2
profile: driftdoctor
model-paths: [\"models\"]
test-paths: [\"tests\"]
macro-paths: [\"macros\"]
clean-targets: [\"target\", \"dbt_packages\"]
models:
  driftdoctor_case:
    +materialized: table
"""

PROFILES_YML = """driftdoctor:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: benchmark.duckdb
      schema: analytics
      threads: 1
"""


def _sources_yaml(tables: list[str]) -> str:
    rows = ["version: 2", "", "sources:", "  - name: raw", "    schema: raw", "    tables:"]
    for table in tables:
        rows.append(f"      - name: {table}")
    return "\n".join(rows) + "\n"


def _base(tables: list[str]) -> dict[str, str]:
    return {
        "dbt_project.yml": PROJECT_YML,
        "profiles.yml": PROFILES_YML,
        "models/sources.yml": _sources_yaml(tables),
    }


def _csv(headers: list[str], rows: list[list[object]]) -> str:
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def _case_001() -> dict[str, str]:
    files = _base(["raw_customers"])
    files.update(
        {
            "input/raw_customers.csv": _csv(
                ["customer_id", "full_name", "revenue_amount"],
                [[1, "Ada Lovelace", 100], [2, "Grace Hopper", 250]],
            ),
            "models/stg_customers.sql": """select
    customer_id,
    customer_name,
    revenue_amount
from {{ source('raw', 'raw_customers') }}
""",
            "models/mart_customer_revenue.sql": """select
    customer_id,
    customer_name,
    revenue_amount
from {{ ref('stg_customers') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: mart_customer_revenue
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_002() -> dict[str, str]:
    files = _base(["raw_customers"])
    files.update(
        {
            "input/raw_customers.csv": _csv(
                ["customer_id", "first_name", "last_name", "revenue_amount"],
                [[1, "Ada", "Lovelace", 100], [2, "Grace", "Hopper", 250]],
            ),
            "models/stg_customers.sql": """select
    customer_id,
    display_name,
    revenue_amount
from {{ source('raw', 'raw_customers') }}
""",
            "models/mart_customers.sql": """select * from {{ ref('stg_customers') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: mart_customers
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
      - name: display_name
        data_tests: [not_null]
""",
        }
    )
    return files


def _case_003() -> dict[str, str]:
    files = _base(["raw_orders"])
    files.update(
        {
            "input/raw_orders.csv": _csv(
                ["order_id", "amount_text"],
                [[1, "100.50"], [2, "not-a-number"], [3, "25.00"]],
            ),
            "models/stg_orders.sql": """select
    order_id,
    amount_text * 1.0 as amount
from {{ source('raw', 'raw_orders') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: stg_orders
    columns:
      - name: order_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_004() -> dict[str, str]:
    files = _base(["raw_orders"])
    files.update(
        {
            "input/raw_orders.csv": _csv(
                ["order_id", "customer_id", "amount"],
                [[1, 10, 100], [2, 20, 50]],
            ),
            "models/stg_orders_v2.sql": """select * from {{ source('raw', 'raw_orders') }}
""",
            "models/mart_orders.sql": """select
    order_id,
    customer_id,
    amount
from {{ ref('stg_orders') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: mart_orders
    columns:
      - name: order_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_005() -> dict[str, str]:
    files = _base(["raw_orders", "raw_customer_tiers"])
    files.update(
        {
            "input/raw_orders.csv": _csv(
                ["order_id", "customer_id", "revenue"],
                [[1, 10, 100], [2, 20, 200]],
            ),
            "input/raw_customer_tiers.csv": _csv(
                ["customer_id", "tier", "effective_at"],
                [[10, "silver", "2026-01-01"], [10, "gold", "2026-08-01"], [20, "silver", "2026-01-01"]],
            ),
            "models/fct_revenue.sql": """select
    o.order_id,
    o.customer_id,
    d.tier,
    o.revenue
from {{ source('raw', 'raw_orders') }} o
left join {{ source('raw', 'raw_customer_tiers') }} d
  on o.customer_id = d.customer_id
""",
            "models/schema.yml": """version: 2
models:
  - name: fct_revenue
    columns:
      - name: order_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_006() -> dict[str, str]:
    files = _base(["raw_customers"])
    files.update(
        {
            "input/raw_customers.csv": _csv(
                ["record_id", "customer_id", "customer_name"],
                [[1, "C001", "Ada"], [2, "", "Unknown"], [3, "C003", "Grace"]],
            ),
            "models/stg_customers.sql": """select
    record_id,
    customer_id,
    customer_name
from {{ source('raw', 'raw_customers') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: stg_customers
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_007() -> dict[str, str]:
    files = _base(["raw_orders"])
    files.update(
        {
            "input/raw_orders.csv": _csv(
                ["order_id", "status"],
                [[1, "paid"], [2, "refunded"], [3, "chargeback"]],
            ),
            "models/stg_order_status.sql": """select
    order_id,
    status,
    case
      when status = 'paid' then 'revenue'
      when status = 'refunded' then 'refund'
      else 'unknown'
    end as business_status
from {{ source('raw', 'raw_orders') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: stg_order_status
    columns:
      - name: order_id
        data_tests: [unique, not_null]
      - name: business_status
        data_tests:
          - accepted_values:
              arguments:
                values: ['revenue', 'refund']
""",
        }
    )
    return files


def _case_008() -> dict[str, str]:
    files = _base(["raw_payments"])
    files.update(
        {
            "input/raw_payments.csv": _csv(
                ["payment_id", "amount_cents"], [[1, 1234], [2, 5000]]
            ),
            "macros/normalize_currency.sql": """{% macro normalize_currency(amount, scale=100) %}
    ({{ amount }} / {{ scale }})
{% endmacro %}
""",
            "models/stg_payments.sql": """select
    payment_id,
    {{ normalize_currency('amount_cents', divisor=100) }} as amount_dollars
from {{ source('raw', 'raw_payments') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: stg_payments
    columns:
      - name: payment_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_009() -> dict[str, str]:
    files = _base(["raw_customer_updates"])
    files.update(
        {
            "input/raw_customer_updates.csv": _csv(
                ["customer_id", "email", "updated_at"],
                [
                    ["C001", "old@example.com", "2026-07-01 10:00:00"],
                    ["C001", "new@example.com", "2026-08-01 10:00:00"],
                    ["C002", "stable@example.com", "2026-07-15 10:00:00"],
                ],
            ),
            "models/current_customers.sql": """select
    customer_id,
    email,
    updated_at
from {{ source('raw', 'raw_customer_updates') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: current_customers
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_010() -> dict[str, str]:
    files = _base(["raw_events"])
    files.update(
        {
            "input/raw_events.csv": _csv(
                ["event_id", "event_ts_utc", "amount"],
                [
                    [1, "2026-08-28 17:00:00", 10],
                    [2, "2026-08-28 18:45:00", 20],
                    [3, "2026-08-29 03:00:00", 30],
                ],
            ),
            "models/daily_events.sql": """select
    event_id,
    cast(event_ts_utc as date) as reporting_date,
    amount
from {{ source('raw', 'raw_events') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: daily_events
    columns:
      - name: event_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


def _case_011() -> dict[str, str]:
    files = _base(["raw_transactions"])
    files.update(
        {
            "input/raw_transactions.csv": _csv(
                ["transaction_id", "kind", "amount"],
                [[1, "sale", 100], [2, "sale", 50], [3, "refund", 20]],
            ),
            "models/revenue_summary.sql": """select
    sum(case when kind = 'sale' then amount else 0 end) as gross_sales,
    sum(case when kind = 'refund' then amount else 0 end) as refunds,
    sum(amount) as net_revenue
from {{ source('raw', 'raw_transactions') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: revenue_summary
    columns:
      - name: gross_sales
        data_tests: [not_null]
      - name: net_revenue
        data_tests: [not_null]
""",
        }
    )
    return files


def _case_012() -> dict[str, str]:
    files = _base(["raw_customer_revenue"])
    files.update(
        {
            "input/raw_customer_revenue.csv": _csv(
                ["customer_id", "client_name", "revenue_text"],
                [[1, "Ada", "100.00"], [2, "Grace", "invalid"], [3, "Linus", "50.00"]],
            ),
            "models/stg_customer_revenue.sql": """select
    customer_id,
    customer_name,
    revenue_text * 1.0 as revenue_amount
from {{ source('raw', 'raw_customer_revenue') }}
""",
            "models/mart_customer_revenue.sql": """select * from {{ ref('stg_customer_revenue') }}
""",
            "models/schema.yml": """version: 2
models:
  - name: mart_customer_revenue
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
""",
        }
    )
    return files


_BUILDERS: dict[str, Callable[[], dict[str, str]]] = {
    "DD-001": _case_001,
    "DD-002": _case_002,
    "DD-003": _case_003,
    "DD-004": _case_004,
    "DD-005": _case_005,
    "DD-006": _case_006,
    "DD-007": _case_007,
    "DD-008": _case_008,
    "DD-009": _case_009,
    "DD-010": _case_010,
    "DD-011": _case_011,
    "DD-012": _case_012,
}


def case_ids() -> list[str]:
    return sorted(_BUILDERS)


def case_files(case_id: str) -> dict[str, str]:
    try:
        return _BUILDERS[case_id]()
    except KeyError as exc:
        raise ValueError(f"Unknown case: {case_id}") from exc


def materialize_case(case_id: str, output: Path, force: bool = False) -> Path:
    output = output.resolve()
    if output.exists():
        if not force:
            raise FileExistsError(f"Output exists: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for relative, content in case_files(case_id).items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    _prepare_duckdb(output)
    (output / ".driftdoctor-case").write_text(case_id + "\n", encoding="utf-8")
    return output


def _prepare_duckdb(output: Path) -> None:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb is required; install requirements.txt first") from exc

    db_path = output / "benchmark.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("create schema if not exists raw")
        con.execute("create schema if not exists analytics")
        for csv_path in sorted((output / "input").glob("*.csv")):
            table = csv_path.stem
            safe_table = table.replace('"', '""')
            safe_path = str(csv_path).replace("'", "''")
            con.execute(
                f'create or replace table raw."{safe_table}" as '
                f"select * from read_csv_auto('{safe_path}', header=true)"
            )
    finally:
        con.close()
