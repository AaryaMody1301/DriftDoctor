from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driftdoctor.repair_skills import propose_contract_patch


class RepairSkillIntegrityTests(unittest.TestCase):
    def test_skill_module_has_no_case_ids_or_evaluator_imports(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "driftdoctor" / "repair_skills.py").read_text(
            encoding="utf-8"
        )
        forbidden = [
            "DD-001",
            "DD-012",
            "benchmark.oracles",
            "reference_repairs",
            "evaluate_case",
            "oracle_checks",
        ]
        for token in forbidden:
            self.assertNotIn(token, source, token)

    def _project(self, files: dict[str, str], csv_text: str = "") -> tuple[tempfile.TemporaryDirectory, Path]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name)
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        if csv_text:
            path = root / "input" / "sample.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(csv_text, encoding="utf-8")
        return holder, root

    def test_source_alias_generalizes_to_unseen_contract_and_source_names(self) -> None:
        holder, root = self._project(
            {"models/stg_accounts.sql": "select\n    account_id,\n    account_label\nfrom {{ source('raw', 'accounts') }}\n"},
            "account_id,canonical_label\n1,Ada\n",
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "The public account contract is `account_id`, `account_label`. Upstream renamed the label field but downstream names stay stable.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("canonical_label as account_label", text)

    def test_derived_display_generalizes_to_unseen_identifiers(self) -> None:
        holder, root = self._project(
            {"models/stg_owners.sql": "select\n    owner_id,\n    owner_display\nfrom {{ source('raw', 'owners') }}\n"},
            "owner_id,given_name,family_name\n1,Ada,Lovelace\n",
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "The model must expose `owner_id`, `owner_display`. `owner_display` is the trimmed concatenation of `given_name`, a single space, and `family_name`.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("trim(given_name || ' ' || family_name) as owner_display", text)

    def test_safe_numeric_generalizes_to_unseen_text_measure(self) -> None:
        holder, root = self._project(
            {"models/stg_prices.sql": "select sku, price_text * 1.0 as price from {{ source('raw', 'prices') }}\n"},
            "sku,price_text\na,12.50\n",
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "price is numeric downstream; invalid numeric text must become NULL instead of failing.",
            )
        text = patch["files"][0]["content"].lower()
        self.assertIn("try_cast(price_text as decimal(18,2)) as price", text)

    def test_missing_ref_generalizes_to_unseen_model_name(self) -> None:
        holder, root = self._project(
            {
                "models/stg_items_v3.sql": "select 1 as item_id\n",
                "models/mart_items.sql": "select * from {{ ref('stg_items') }}\n",
            }
        )
        with holder:
            patch = propose_contract_patch(root, "Use the current staging model after its refactor rename.")
        changed = {item["path"]: item["content"] for item in patch["files"]}
        self.assertIn("ref('stg_items_v3')", changed["models/mart_items.sql"])

    def test_required_identifier_uses_identifier_from_contract(self) -> None:
        holder, root = self._project(
            {"models/stg_accounts.sql": "select account_key, value from {{ source('raw', 'accounts') }}\n"},
            "account_key,value\n,1\n",
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "`account_key` is required. Source rows with NULL, empty, or whitespace-only account keys are invalid and must be excluded.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("trim(cast(account_key as varchar))", text)

    def test_latest_record_uses_contract_key_and_timestamp(self) -> None:
        holder, root = self._project(
            {"models/current_accounts.sql": "select account_key, changed_at, value from {{ source('raw', 'accounts') }}\n"},
            "account_key,changed_at,value\n1,2026-01-01,old\n1,2026-01-02,new\n",
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "The model contract is exactly one current row per `account_key`. If multiple records exist, choose the row with the greatest `changed_at`.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("partition by account_key order by changed_at desc", text)

    def test_timezone_skill_uses_zone_and_output_alias_from_project(self) -> None:
        holder, root = self._project(
            {
                "models/daily_events.sql": (
                    "select cast(event_ts_utc as date) as local_day "
                    "from {{ source('raw', 'events') }}\n"
                )
            }
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "Local calendar dates use Europe/Berlin. Source timestamps are UTC; convert before casting to DATE.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("Europe/Berlin", text)
        self.assertIn("as local_day", text)
        self.assertIn("timezone('UTC'", text)

    def test_patch_targets_only_existing_project_files(self) -> None:
        holder, root = self._project(
            {"models/mart_items.sql": "select * from {{ ref('missing_items') }}\n"}
        )
        with holder:
            patch = propose_contract_patch(root, "Preserve the existing public model contract.")
            existing = {
                str(path.relative_to(root))
                for path in root.glob("models/**/*")
                if path.is_file()
            }
        self.assertTrue(all(item["path"] in existing for item in patch["files"]))


if __name__ == "__main__":
    unittest.main()
