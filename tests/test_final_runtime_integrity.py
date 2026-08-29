from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driftdoctor.v4 import run_v4

ROOT = Path(__file__).resolve().parents[1]
FINAL_RUNTIME = [
    "driftdoctor/repair_skills.py",
    "driftdoctor/contract_checks.py",
    "driftdoctor/ambiguity.py",
    "driftdoctor/v4.py",
]


class FinalRuntimeIntegrityTests(unittest.TestCase):
    def test_no_benchmark_case_ids_or_evaluator_imports(self) -> None:
        for relative in FINAL_RUNTIME:
            text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
            self.assertIsNone(re.search(r"\bDD-\d{3}\b", text), relative)
            self.assertIsNone(re.search(r"(?m)^\s*(?:from|import)\s+benchmark(?:\.|\s)", text), relative)
            for forbidden in ("reference_repairs", "oracle_checks", "evaluate_case"):
                self.assertNotIn(forbidden, text, f"{relative}: {forbidden}")

    def test_final_runtime_does_not_import_historical_open_ended_agent(self) -> None:
        text = (ROOT / "driftdoctor" / "v4.py").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("run_v3", text)
        self.assertNotIn("from driftdoctor.v3", text)

    def test_zero_model_budget_never_invokes_the_ambiguity_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "driftdoctor.v4._run_build", return_value={"returncode": 2, "stdout": "", "stderr": "broken"}
        ), patch(
            "driftdoctor.v4.propose_contract_patch",
            return_value={"root_cause_class": "unknown", "skills": [], "files": []},
        ), patch("driftdoctor.v4.resolve_ambiguous_missing_ref") as resolver:
            result = run_v4(
                Path(tmp),
                "broken dependency",
                "test-model",
                max_model_calls=0,
                allow_fallback=True,
            )
        resolver.assert_not_called()
        self.assertEqual(result["model_calls"], 0)
        self.assertFalse(result["fallback_used"])
        self.assertTrue(result["escalation_required"])

    def test_negative_model_budget_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            run_v4(Path(tmp), "incident", "test-model", max_model_calls=-1)


if __name__ == "__main__":
    unittest.main()
