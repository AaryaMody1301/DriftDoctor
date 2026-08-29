from __future__ import annotations

import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_incident


class RunIncidentSafetyTests(unittest.TestCase):
    def _write_profile(self, root: Path, target_body: str) -> None:
        (root / "dbt_project.yml").write_text(
            "name: demo\nprofile: demo_profile\n", encoding="utf-8"
        )
        (root / "profiles.yml").write_text(
            "demo_profile:\n  target: dev\n  outputs:\n    dev:\n" + target_body,
            encoding="utf-8",
        )

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

    def test_judge_cli_accepts_relative_and_in_memory_duckdb_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_profile(
                root,
                "      type: duckdb\n      path: demo.duckdb\n      schema: analytics\n      threads: 1\n",
            )
            run_incident._validate_local_duckdb_profile(root)

            self._write_profile(root, "      type: duckdb\n")
            run_incident._validate_local_duckdb_profile(root)

            self._write_profile(root, "      type: duckdb\n      path: ':memory:'\n")
            run_incident._validate_local_duckdb_profile(root)

    def test_judge_cli_rejects_non_duckdb_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_profile(
                root,
                "      type: snowflake\n      account: example\n",
            )
            with self.assertRaises(SystemExit):
                run_incident._validate_local_duckdb_profile(root)

    def test_judge_cli_rejects_remote_absolute_dynamic_and_escaping_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unsafe_paths = [
                "md:production",
                "/tmp/outside.duckdb",
                "../outside.duckdb",
                "{{ env_var('DB_PATH') }}",
                "s3://bucket/state.duckdb",
            ]
            for unsafe in unsafe_paths:
                with self.subTest(path=unsafe):
                    self._write_profile(
                        root,
                        f"      type: duckdb\n      path: \"{unsafe}\"\n",
                    )
                    with self.assertRaises(SystemExit):
                        run_incident._validate_local_duckdb_profile(root)

    def test_judge_cli_rejects_duckdb_remote_or_extension_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unsafe_fields = {
                "attach": "      attach: []\n",
                "extensions": "      extensions: [httpfs]\n",
                "filesystems": "      filesystems: []\n",
                "plugins": "      plugins: []\n",
                "secrets": "      secrets: []\n",
                "settings": "      settings:\n        enable_external_access: true\n",
            }
            for name, extra in unsafe_fields.items():
                with self.subTest(field=name):
                    self._write_profile(root, "      type: duckdb\n" + extra)
                    with self.assertRaises(SystemExit):
                        run_incident._validate_local_duckdb_profile(root)

    def test_judge_cli_rejects_hooks_python_models_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_profile(root, "      type: duckdb\n")
            (root / "dbt_project.yml").write_text(
                "name: demo\nprofile: demo_profile\non-run-start: ['select 1']\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                run_incident._validate_local_duckdb_profile(root)

            (root / "dbt_project.yml").write_text(
                "name: demo\nprofile: demo_profile\n", encoding="utf-8"
            )
            models = root / "models"
            models.mkdir()
            (models / "unsafe.py").write_text("def model(dbt, session): return None\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                run_incident._validate_project_tree(root)
            (models / "unsafe.py").unlink()

            if hasattr(os, "symlink"):
                target = root / "target.sql"
                target.write_text("select 1\n", encoding="utf-8")
                link = models / "linked.sql"
                try:
                    link.symlink_to(target)
                except OSError:
                    self.skipTest("symlinks are unavailable in this environment")
                with self.assertRaises(SystemExit):
                    run_incident._validate_project_tree(root)

    def test_approval_diff_excludes_generated_duckdb_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "models").mkdir()
            model = root / "models" / "example.sql"
            database = root / "state.duckdb"
            wal = root / "state.duckdb.wal"
            model.write_text("select 1 as value\n", encoding="utf-8")
            database.write_bytes(b"before")
            wal.write_bytes(b"before")
            run_incident._init_snapshot(root)

            model.write_text("select 2 as value\n", encoding="utf-8")
            database.write_bytes(b"after")
            wal.write_bytes(b"after")
            diff = run_incident._diff(root)

            self.assertIn("models/example.sql", diff)
            self.assertNotIn("state.duckdb", diff)
            self.assertNotIn("state.duckdb.wal", diff)


if __name__ == "__main__":
    unittest.main()
