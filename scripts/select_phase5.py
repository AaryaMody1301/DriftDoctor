#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

SYSTEMS = ["context-baseline", "driftdoctor-no-review", "driftdoctor-review"]


def _load_summary(root: Path, system: str) -> dict:
    path = root / system / "summary.json"
    if not path.is_file():
        raise SystemExit(f"missing Phase 5 summary: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("system") != system:
        raise SystemExit(f"summary system mismatch for {system}: {data.get('system')!r}")
    if data.get("complete") is not True:
        raise SystemExit(f"{system} is incomplete")
    if data.get("expected_cases") != 12 or data.get("scored_cases") != 12:
        raise SystemExit(f"{system} must score exactly 12/12 cases")
    if data.get("infrastructure_errors"):
        raise SystemExit(f"{system} contains infrastructure errors")
    if data.get("verified_resolution_rate") is None:
        raise SystemExit(f"{system} has no publishable VRR")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the frozen Phase 5 winner rule: VRR, then fewer calls, then lower latency."
    )
    parser.add_argument(
        "--results-root",
        default="benchmark/results/phase5",
        help="Directory containing one subdirectory per Phase 5 system.",
    )
    parser.add_argument(
        "--output",
        default="benchmark/results/phase5/final-selection.json",
    )
    args = parser.parse_args()

    root = Path(args.results_root)
    summaries = {system: _load_summary(root, system) for system in SYSTEMS}

    ranking = sorted(
        SYSTEMS,
        key=lambda system: (
            -float(summaries[system]["verified_resolution_rate"]),
            float(summaries[system]["mean_model_calls"]),
            float(summaries[system]["mean_elapsed_seconds"]),
        ),
    )
    winner = ranking[0]
    comparison = []
    for system in ranking:
        data = summaries[system]
        comparison.append({
            "system": system,
            "verified_resolution_rate": data["verified_resolution_rate"],
            "solved": data.get("solved"),
            "root_cause_accuracy": data.get("root_cause_accuracy"),
            "mean_model_calls": data.get("mean_model_calls"),
            "mean_elapsed_seconds": data.get("mean_elapsed_seconds"),
        })

    output = {
        "selection_rule": [
            "highest verified_resolution_rate",
            "fewest mean_model_calls",
            "lowest mean_elapsed_seconds",
        ],
        "winner": winner,
        "ranking": ranking,
        "comparison": comparison,
        "semantic_review_selected": winner == "driftdoctor-review",
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
