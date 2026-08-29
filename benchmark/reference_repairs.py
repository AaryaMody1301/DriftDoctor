"""Evaluator-only reference repairs used to smoke-test benchmark solvability.

These repairs are never copied into a materialized agent workspace.
"""
from __future__ import annotations

from pathlib import Path

_REPAIRS: dict[str, dict[str, str]] = {
    "DD-001": {
        "models/stg_customers.sql": """select
    customer_id,
    full_name as customer_name,
    revenue_amount
from {{ source('raw', 'raw_customers') }}
""",
    },
    "DD-002": {
        "models/stg_customers.sql": """select
    customer_id,
    trim(first_name || ' ' || last_name) as display_name,
    revenue_amount
from {{ source('raw', 'raw_customers') }}
""",
    },
    "DD-003": {
        "models/stg_orders.sql": """select
    order_id,
    try_cast(amount_text as decimal(12, 2)) as amount
from {{ source('raw', 'raw_orders') }}
""",
    },
    "DD-004": {
        "models/mart_orders.sql": """select
    order_id,
    customer_id,
    amount
from {{ ref('stg_orders_v2') }}
""",
    },
    "DD-005": {
        "models/fct_revenue.sql": """with current_tier as (
    select customer_id, tier
    from {{ source('raw', 'raw_customer_tiers') }}
    qualify row_number() over (
        partition by customer_id order by effective_at desc
    ) = 1
)
select
    o.order_id,
    o.customer_id,
    d.tier,
    o.revenue
from {{ source('raw', 'raw_orders') }} o
left join current_tier d
  on o.customer_id = d.customer_id
""",
    },
    "DD-006": {
        "models/stg_customers.sql": """select
    record_id,
    customer_id,
    customer_name
from {{ source('raw', 'raw_customers') }}
where nullif(trim(customer_id), '') is not null
""",
    },
    "DD-007": {
        "models/stg_order_status.sql": """select
    order_id,
    status,
    case
      when status = 'paid' then 'revenue'
      when status = 'refunded' then 'refund'
      when status = 'chargeback' then 'loss'
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
                values: ['revenue', 'refund', 'loss']
""",
    },
    "DD-008": {
        "models/stg_payments.sql": """select
    payment_id,
    {{ normalize_currency('amount_cents', scale=100) }} as amount_dollars
from {{ source('raw', 'raw_payments') }}
""",
    },
    "DD-009": {
        "models/current_customers.sql": """select
    customer_id,
    email,
    updated_at
from {{ source('raw', 'raw_customer_updates') }}
qualify row_number() over (
    partition by customer_id order by updated_at desc
) = 1
""",
    },
    "DD-010": {
        "models/daily_events.sql": """select
    event_id,
    cast(
      timezone('Asia/Kolkata', event_ts_utc::timestamp at time zone 'UTC')
      as date
    ) as reporting_date,
    amount
from {{ source('raw', 'raw_events') }}
""",
    },
    "DD-011": {
        "models/revenue_summary.sql": """select
    sum(case when kind = 'sale' then amount else 0 end) as gross_sales,
    sum(case when kind = 'refund' then amount else 0 end) as refunds,
    sum(case when kind = 'refund' then -amount else amount end) as net_revenue
from {{ source('raw', 'raw_transactions') }}
""",
    },
    "DD-012": {
        "models/stg_customer_revenue.sql": """select
    customer_id,
    client_name as customer_name,
    try_cast(revenue_text as decimal(12, 2)) as revenue_amount
from {{ source('raw', 'raw_customer_revenue') }}
""",
    },
}


def apply_reference_repair(case_id: str, workdir: Path) -> None:
    try:
        changes = _REPAIRS[case_id]
    except KeyError as exc:
        raise ValueError(f"Unknown case: {case_id}") from exc
    for relative, content in changes.items():
        target = workdir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
