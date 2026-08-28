#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.fixture_factory import case_ids, materialize_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize a DriftDoctor benchmark case")
    parser.add_argument("case_id", nargs="?", choices=case_ids())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\n".join(case_ids()))
        return 0
    if not args.case_id:
        parser.error("case_id is required unless --list is used")

    output = args.output or ROOT / ".work" / args.case_id
    path = materialize_case(args.case_id, output, force=args.force)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
