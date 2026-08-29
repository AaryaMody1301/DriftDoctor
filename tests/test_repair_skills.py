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

    def test_source_alias_generalizes_to_unseen_name_column(self) -> None:
        holder, root = self._project(
            {"models/stg_people.sql": "select\n    person_id,\n    customer_name\nfrom {{ source('raw', 'people') }}\n"},
            "person_id,legal_name\n1,Ada\n",
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "The downstream contract keeps customer_name stable even though the upstream name field was renamed.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("legal_name as customer_name", text)

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

    def test_timezone_skill_uses_zone_from_contract(self) -> None:
        holder, root = self._project(
            {
                "models/daily_events.sql": (
                    "select cast(event_ts_utc as date) as reporting_date "
                    "from {{ source('raw', 'events') }}\n"
                )
            }
        )
        with holder:
            patch = propose_contract_patch(
                root,
                "Reporting dates use Europe/Berlin local calendar dates. Source timestamps are UTC.",
            )
        text = patch["files"][0]["content"]
        self.assertIn("Europe/Berlin", text)
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
