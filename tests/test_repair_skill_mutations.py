from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driftdoctor.repair_skills import propose_contract_patch


class RepairSkillMutationTests(unittest.TestCase):
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

    def test_scd_join_skill_generalizes_to_alternative_keys(self) -> None:
        holder, root = self._project(
            {
                "models/fact_invoices.sql": (
                    "select i.invoice_id, i.amount, t.segment\n"
                    "from {{ source('raw', 'invoices') }} i\n"
                    "left join {{ source('raw', 'account_tiers') }} t\n"
                    "  on i.account_key = t.account_key\n"
                )
            }
        )
        context = (
            "Account tier is a slowly changing attribute; when multiple tier records exist, "
            "use the record with the greatest `valid_from` for that account."
        )
        with holder:
            patch = propose_contract_patch(root, context)
        text = patch["files"][0]["content"].lower()
        self.assertIn("partition by account_key order by valid_from desc", text)
        self.assertIn("driftdoctor_latest_dimension", text)

    def test_categorical_mapping_updates_logic_and_validation(self) -> None:
        holder, root = self._project(
            {
                "models/stg_cases.sql": (
                    "select case when raw_state = 'queued' then 'pending' else 'unknown' end as state "
                    "from {{ source('raw', 'cases') }}\n"
                ),
                "models/schema.yml": "accepted_values:\n  arguments:\n    values: ['pending']\n",
            }
        )
        context = "Business mapping is `queued -> pending`, `done -> complete`. Validation must stay explicit."
        with holder:
            patch = propose_contract_patch(root, context)
        changed = {item["path"]: item["content"] for item in patch["files"]}
        self.assertIn("when raw_state = 'done' then 'complete'", changed["models/stg_cases.sql"])
        self.assertIn("'complete'", changed["models/schema.yml"])

    def test_macro_interface_skill_uses_contract_keyword(self) -> None:
        holder, root = self._project(
            {
                "macros/normalize.sql": "{% macro normalize(value, divisor=10) %} {{ value }} / {{ divisor }} {% endmacro %}\n",
                "models/mart.sql": "select {{ normalize(amount, factor=10) }} as amount from {{ ref('base') }}\n",
                "models/base.sql": "select 100 as amount\n",
            }
        )
        context = "The shared macro accepts keyword argument `divisor`; use divisor=10 at the call site."
        with holder:
            patch = propose_contract_patch(root, context)
        changed = {item["path"]: item["content"] for item in patch["files"]}
        self.assertIn("normalize(amount, divisor=10)", changed["models/mart.sql"])

    def test_business_formula_skill_uses_alternative_accounting_terms(self) -> None:
        holder, root = self._project(
            {
                "models/mart_balance.sql": (
                    "select\n"
                    "  sum(case when kind = 'credit' then amount else 0 end) as credits,\n"
                    "  sum(case when kind = 'debit' then amount else 0 end) as debits,\n"
                    "  sum(amount) as balance\n"
                    "from {{ source('raw', 'ledger') }}\n"
                )
            }
        )
        context = "Source amounts are positive magnitudes. `balance = credits - debits`."
        with holder:
            patch = propose_contract_patch(root, context)
        text = patch["files"][0]["content"].lower()
        self.assertIn("-", text)
        self.assertIn("as balance", text)
        self.assertIn("kind = 'credit'", text)
        self.assertIn("kind = 'debit'", text)


if __name__ == "__main__":
    unittest.main()
