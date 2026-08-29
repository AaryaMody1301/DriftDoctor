from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driftdoctor.ambiguity import find_ambiguous_missing_ref, resolve_ambiguous_missing_ref


class AmbiguityResolverTests(unittest.TestCase):
    def _project(self, downstream_sql: str | None = None) -> tuple[tempfile.TemporaryDirectory, Path]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name)
        (root / "models").mkdir(parents=True)
        (root / "models" / "stg_shipments_v2.sql").write_text("select 1 as shipment_id\n", encoding="utf-8")
        (root / "models" / "stg_shipments_archive.sql").write_text("select 0 as shipment_id\n", encoding="utf-8")
        (root / "models" / "mart_shipments.sql").write_text(
            downstream_sql or "select * from {{ ref('stg_shipments') }}\n", encoding="utf-8"
        )
        return holder, root

    def test_detector_exposes_candidates_without_choosing(self) -> None:
        holder, root = self._project()
        with holder:
            ambiguity = find_ambiguous_missing_ref(root)
        self.assertIsNotNone(ambiguity)
        assert ambiguity is not None
        self.assertEqual(ambiguity["missing_ref"], "stg_shipments")
        self.assertEqual(ambiguity["candidates"], ["stg_shipments_archive", "stg_shipments_v2"])

    def test_detector_handles_whitespace_and_repeated_same_ref_as_one_ambiguity(self) -> None:
        holder, root = self._project(
            "select * from {{ ref ( \"stg_shipments\" ) }}\n"
            "union all select * from {{ ref('stg_shipments') }}\n"
        )
        with holder:
            ambiguity = find_ambiguous_missing_ref(root)
        self.assertIsNotNone(ambiguity)
        assert ambiguity is not None
        self.assertEqual(ambiguity["missing_ref"], "stg_shipments")

    def test_agent_selection_is_constrained_to_observed_candidate(self) -> None:
        holder, root = self._project()
        with holder, patch(
            "driftdoctor.ambiguity._chat",
            return_value={
                "selection": "stg_shipments_v2",
                "reason": "The visible contract marks v2 as current.",
                "evidence": ["business_context:current=v2"],
            },
        ) as chat:
            result = resolve_ambiguous_missing_ref(
                root,
                "The live mart broke after a dependency refactor.",
                "Use `stg_shipments_v2` for the live mart; the archive is historical.",
                "test-model",
            )
        self.assertTrue(result["handled"])
        self.assertEqual(result["model_calls"], 1)
        self.assertIn("ref('stg_shipments_v2')", result["patch"]["files"][0]["content"])
        schema = chat.call_args.args[2]
        self.assertEqual(
            set(schema["properties"]["selection"]["enum"]),
            {"stg_shipments_archive", "stg_shipments_v2", "abstain"},
        )

    def test_agent_replaces_every_occurrence_without_reformatting_the_ref(self) -> None:
        holder, root = self._project(
            "select * from {{ ref ( \"stg_shipments\" ) }}\n"
            "union all select * from {{ ref('stg_shipments') }}\n"
        )
        with holder, patch(
            "driftdoctor.ambiguity._chat",
            return_value={"selection": "stg_shipments_v2", "reason": "current", "evidence": []},
        ):
            result = resolve_ambiguous_missing_ref(root, "Broken ref", "v2 is current", "test-model")
        self.assertTrue(result["handled"])
        content = result["patch"]["files"][0]["content"]
        self.assertEqual(content.count("stg_shipments_v2"), 2)
        self.assertNotIn("stg_shipments\"", content)
        self.assertNotIn("stg_shipments'", content)

    def test_agent_can_abstain_without_creating_patch(self) -> None:
        holder, root = self._project()
        with holder, patch(
            "driftdoctor.ambiguity._chat",
            return_value={"selection": "abstain", "reason": "Insufficient evidence.", "evidence": []},
        ):
            result = resolve_ambiguous_missing_ref(root, "Broken ref", "No rule identifies the current model.", "test-model")
        self.assertFalse(result["handled"])
        self.assertEqual(result["model_calls"], 1)
        self.assertNotIn("patch", result)

    def test_invalid_model_output_cannot_invent_dependency(self) -> None:
        holder, root = self._project()
        with holder, patch(
            "driftdoctor.ambiguity._chat",
            return_value={"selection": "stg_shipments_v99", "reason": "invented", "evidence": []},
        ):
            result = resolve_ambiguous_missing_ref(root, "Broken ref", "Use current model.", "test-model")
        self.assertFalse(result["handled"])
        self.assertNotIn("patch", result)


if __name__ == "__main__":
    unittest.main()
