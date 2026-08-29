from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_incident


class RunIncidentSafetyTests(unittest.TestCase):
    def test_empty_inline_incident_is_rejected(self) -> None:
        args = argparse.Namespace(incident="   ", incident_file=None)
        with self.assertRaises(SystemExit):
            run_incident._incident_text(args)

    def test_missing_incident_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(
                incident=None,
                incident_file=str(Path(tmp) / "missing.txt"),
            )
            with self.assertRaises(SystemExit):
                run_incident._incident_text(args)

    def test_force_refuses_unowned_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            (source / "dbt_project.yml").write_text("name: example\n", encoding="utf-8")
            sandbox = base / "existing"
            sandbox.mkdir()
            sentinel = sandbox / "do-not-delete.txt"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaises(SystemExit):
                run_incident._prepare_sandbox(source, sandbox, force=True)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_force_replaces_only_owned_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            (source / "model.sql").write_text("select 1\n", encoding="utf-8")

            sandbox = base / "sandbox"
            sandbox.mkdir()
            (sandbox / run_incident.SANDBOX_MARKER).write_text("owned\n", encoding="utf-8")
            (sandbox / "old.txt").write_text("old\n", encoding="utf-8")

            run_incident._prepare_sandbox(source, sandbox, force=True)

            self.assertTrue((sandbox / run_incident.SANDBOX_MARKER).is_file())
            self.assertTrue((sandbox / "model.sql").is_file())
            self.assertFalse((sandbox / "old.txt").exists())

    def test_sandbox_cannot_contain_source_or_live_inside_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()

            with self.assertRaises(SystemExit):
                run_incident._validate_sandbox_target(source, base)
            with self.assertRaises(SystemExit):
                run_incident._validate_sandbox_target(source, source / "nested")


if __name__ == "__main__":
    unittest.main()
