from __future__ import annotations

import re
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
