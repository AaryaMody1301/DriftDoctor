from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driftdoctor.contract_checks import semantic_concerns


class ContractCheckTests(unittest.TestCase):
    def _project(self, files: dict[str, str], csv_text: str = "") -> tuple[tempfile.TemporaryDirectory, Path]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name)
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        if csv_text:
            target = root / "input" / "sample.csv"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(csv_text, encoding="utf-8")
        return holder, root

    def test_derivation_and_stable_alias_use_contract_identifiers(self) -> None:
        holder, root = self._project(
            {
                "models/stg_people.sql": (
                    "select person_id, trim(given || ' ' || family) as public_label "
                    "from {{ source('raw', 'people') }}\n"
                )
            },
            "person_id,given,family\n1,Ada,Lovelace\n",
        )
        context = (
            "The public contract is `person_id`, `public_label`. "
            "`public_label` is the trimmed concatenation of `given`, a space, and `family`."
        )
        with holder:
            self.assertEqual(semantic_concerns(root, context), [])

    def test_required_identifier_and_mapping_are_parsed_generically(self) -> None:
        holder, root = self._project(
            {
                "models/stg_cases.sql": (
                    "select case_key, case when raw_state = 'queued' then 'pending' "
                    "when raw_state = 'done' then 'complete' else 'unknown' end as state "
                    "from {{ source('raw', 'cases') }} "
                    "where nullif(trim(cast(case_key as varchar)), '') is not null\n"
                ),
                "models/schema.yml": (
                    "version: 2\nmodels:\n  - name: stg_cases\n    columns:\n      - name: state\n"
                    "        data_tests:\n          - accepted_values:\n              arguments:\n"
                    "                values: ['pending', 'complete']\n"
                ),
            },
            "case_key,raw_state\n1,queued\n",
        )
        context = (
            "`case_key` is required. Source rows with NULL, empty, or whitespace-only case keys are invalid and must be excluded. "
            "Business mapping is: `queued -> pending`, `done -> complete`. Validation must remain explicit."
        )
        with holder:
            self.assertEqual(semantic_concerns(root, context), [])

    def test_macro_latest_timezone_and_formula_are_not_name_specific(self) -> None:
        holder, root = self._project(
            {
                "macros/normalize.sql": "{% macro normalize(value, divisor=10) %} {{ value }} / {{ divisor }} {% endmacro %}\n",
                "models/current_metrics.sql": (
                    "select account_key, changed_at, "
                    "cast(timezone('Europe/Berlin', timezone('UTC', cast(event_time as timestamp))) as date) as local_day, "
                    "sum(case when kind = 'credit' then amount else 0 end) - "
                    "sum(case when kind = 'debit' then amount else 0 end) as balance, "
                    "{{ normalize(amount, divisor=10) }} as normalized_amount "
                    "from {{ source('raw', 'metrics') }} "
                    "qualify row_number() over (partition by account_key order by changed_at desc) = 1\n"
                ),
            }
        )
        context = (
            "The shared macro uses keyword argument `divisor`; call it with divisor=10. "
            "The model contract is one current row per `account_key`; choose the row with the greatest `changed_at`. "
            "Local calendar dates use Europe/Berlin. Source timestamps are UTC; convert before casting to DATE. "
            "`balance = credits - debits`."
        )
        with holder:
            self.assertEqual(semantic_concerns(root, context), [])

    def test_missing_contract_behavior_produces_actionable_concerns(self) -> None:
        holder, root = self._project(
            {"models/broken.sql": "select account_key, cast(event_time as date) as local_day from {{ source('raw', 'x') }}\n"},
            "account_key,event_time\n1,2026-01-01 00:00:00\n",
        )
        context = (
            "The model contract is one current row per `account_key`; choose the row with the greatest `changed_at`. "
            "Local calendar dates use America/New_York. Source timestamps are UTC; convert before casting to DATE."
        )
        with holder:
            concerns = semantic_concerns(root, context)
        self.assertTrue(any("changed_at" in concern for concern in concerns))
        self.assertTrue(any("america/new_york" in concern.lower() for concern in concerns))


if __name__ == "__main__":
    unittest.main()
