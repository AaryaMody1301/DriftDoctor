#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.oracles import dump_result, evaluate_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the external DriftDoctor oracle")
    parser.add_argument("case_id")
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    result = evaluate_case(args.case_id, args.workdir, timeout_seconds=args.timeout)
    if args.json_path:
        dump_result(result, args.json_path)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
