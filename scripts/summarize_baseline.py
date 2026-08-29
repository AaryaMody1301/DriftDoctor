#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    records = []
    for path in sorted(args.results.glob("DD-*.json")):
        records.append(json.loads(path.read_text()))
    if not records:
        raise SystemExit("no baseline case records found")

    solved = sum(bool(r["passed"]) for r in records)
    roots = sum(bool(r["root_cause_correct"]) for r in records)
    total = len(records)
    elapsed = sum(float(r["elapsed_seconds"]) for r in records)
    steps = sum(int(r["steps"]) for r in records)
    summary = {
        "system": records[0]["system"],
        "model": records[0]["model"],
        "cases": total,
        "solved": solved,
        "verified_resolution_rate": solved / total,
        "root_cause_correct": roots,
        "root_cause_accuracy": roots / total,
        "total_elapsed_seconds": round(elapsed, 3),
        "mean_elapsed_seconds": round(elapsed / total, 3),
        "mean_steps": round(steps / total, 3),
    }
    (args.results / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))

    lines = [
        "# Baseline v0.1 measurement",
        "",
        f"- Model: `{summary['model']}`",
        f"- Verified Resolution Rate: **{solved}/{total} ({summary['verified_resolution_rate']:.1%})**",
        f"- Root-cause accuracy: **{roots}/{total} ({summary['root_cause_accuracy']:.1%})**",
        f"- Mean elapsed time: **{summary['mean_elapsed_seconds']:.1f}s/case**",
        f"- Mean agent steps: **{summary['mean_steps']:.1f}**",
        "",
        "| Case | Verified | Root cause | Seconds | Steps |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in records:
        lines.append(f"| {r['case_id']} | {'yes' if r['passed'] else 'no'} | {'yes' if r['root_cause_correct'] else 'no'} | {r['elapsed_seconds']:.1f} | {r['steps']} |")
    lines += ["", "> Every case-level JSON contains the full trajectory, final diff, and external oracle output."]
    markdown = "\n".join(lines) + "\n"
    target = args.markdown or args.results / "REPORT.md"
    target.write_text(markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
