#!/usr/bin/env python3
"""Validate the frozen DriftDoctor benchmark contract using stdlib only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "benchmark" / "cases.json"
REQUIRED_CASE_FIELDS = {
    "id",
    "title",
    "category",
    "difficulty",
    "challenge_case",
    "incident",
    "root_cause_class",
    "fault",
    "oracle_checks",
}
ROOT_CAUSE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not CASES_PATH.exists():
        fail(f"missing benchmark file: {CASES_PATH}")

    try:
        payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")

    if payload.get("project") != "DriftDoctor":
        fail("project must be 'DriftDoctor'")
    if payload.get("primary_metric") != "verified_resolution_rate":
        fail("primary_metric must remain 'verified_resolution_rate'")

    environment = payload.get("environment")
    if not isinstance(environment, dict):
        fail("environment must be an object")
    if environment.get("warehouse") != "duckdb":
        fail("Phase 1 benchmark warehouse must be DuckDB")
    if environment.get("data_policy") != "synthetic_only":
        fail("benchmark data policy must be synthetic_only")
    if environment.get("network_required_for_case_execution") is not False:
        fail("benchmark cases must not require network access")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        fail("cases must be a list")
    if len(cases) != 12:
        fail(f"Phase 1 freezes exactly 12 cases; found {len(cases)}")

    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    challenge_ids: list[str] = []

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            fail(f"case #{index} must be an object")

        missing = REQUIRED_CASE_FIELDS - case.keys()
        if missing:
            fail(f"case #{index} missing fields: {sorted(missing)}")

        expected_id = f"DD-{index:03d}"
        case_id = case["id"]
        if case_id != expected_id:
            fail(f"case #{index} must have id {expected_id}; found {case_id!r}")
        if case_id in seen_ids:
            fail(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        title = case["title"]
        if not isinstance(title, str) or not title.strip():
            fail(f"{case_id}: title must be a non-empty string")
        if title in seen_titles:
            fail(f"duplicate case title: {title}")
        seen_titles.add(title)

        if not isinstance(case["incident"], str) or len(case["incident"].strip()) < 40:
            fail(f"{case_id}: incident statement is too short")

        root_cause = case["root_cause_class"]
        if not isinstance(root_cause, str) or not ROOT_CAUSE_RE.fullmatch(root_cause):
            fail(f"{case_id}: root_cause_class must be snake_case")

        if not isinstance(case["fault"], str) or not case["fault"].strip():
            fail(f"{case_id}: fault must be documented")

        checks = case["oracle_checks"]
        if not isinstance(checks, list) or len(checks) < 3:
            fail(f"{case_id}: at least three oracle checks are required")
        if not all(isinstance(check, str) and check.strip() for check in checks):
            fail(f"{case_id}: oracle checks must be non-empty strings")

        if not isinstance(case["challenge_case"], bool):
            fail(f"{case_id}: challenge_case must be boolean")
        if case["challenge_case"]:
            challenge_ids.append(case_id)

    if challenge_ids != ["DD-012"]:
        fail(f"DD-012 must be the single challenge case; found {challenge_ids}")

    print("DriftDoctor benchmark contract is valid.")
    print(f"Cases: {len(cases)}")
    print(f"Challenge case: {challenge_ids[0]}")
    print("Primary metric: verified_resolution_rate")


if __name__ == "__main__":
    main()
