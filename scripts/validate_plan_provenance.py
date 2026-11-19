#!/usr/bin/env python3
"""Validate plan provenance claims against trusted deployment identity."""

import argparse
import json
import re
import sys
from pathlib import Path

SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
MAX_RECORD_BYTES = 64 * 1024

REQUIRED_FIELDS = {
    "source_commit",
    "workflow_run_id",
    "workflow_run_attempt",
    "terraform_version",
    "plan_sha256",
}


class ProvenanceValidationError(Exception):
    """The plan provenance contract was not satisfied."""


def validate_provenance(
    record: dict,
    *,
    authorized_commit: str,
    authorized_run_id: str,
    authorized_run_attempt: str,
    expected_version: str,
    expected_digest: str,
) -> None:
    """Reject malformed or unauthorized plan provenance claims."""
    if not isinstance(record, dict):
        raise ProvenanceValidationError("Provenance must be a JSON object")

    if set(record) != REQUIRED_FIELDS:
        raise ProvenanceValidationError("Unexpected provenance fields")

    if not SHA_PATTERN.fullmatch(authorized_commit):
        raise ProvenanceValidationError("Invalid authorized commit")

    if not DIGEST_PATTERN.fullmatch(expected_digest):
        raise ProvenanceValidationError("Invalid trusted digest")

    for value, label in (
        (authorized_run_id, "run ID"),
        (authorized_run_attempt, "run attempt"),
    ):
        if not value.isascii() or not value.isdecimal() or int(value) < 1:
            raise ProvenanceValidationError(f"Invalid authorized {label}")

    if not expected_version:
        raise ProvenanceValidationError("Missing expected Terraform version")

    for field in REQUIRED_FIELDS:
        if not isinstance(record[field], str):
            raise ProvenanceValidationError(f"Invalid field type: {field}")

    if record["source_commit"] != authorized_commit:
        raise ProvenanceValidationError("Unauthorized source commit")

    if record["workflow_run_id"] != authorized_run_id:
        raise ProvenanceValidationError("Unauthorized workflow run")

    if record["workflow_run_attempt"] != authorized_run_attempt:
        raise ProvenanceValidationError("Unauthorized workflow attempt")

    if record["terraform_version"] != expected_version:
        raise ProvenanceValidationError("Terraform version mismatch")

    if record["plan_sha256"] != expected_digest:
        raise ProvenanceValidationError("Trusted plan digest mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Terraform plan provenance identity."
    )
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--authorized-commit", required=True)
    parser.add_argument("--authorized-run-id", required=True)
    parser.add_argument("--authorized-run-attempt", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-digest", required=True)
    args = parser.parse_args()

    try:
        # This standalone CLI is a local contract-testing tool.
        # The record path is NOT yet a hardened CI artifact boundary.
        with args.record.open("rb") as handle:
            raw = handle.read(MAX_RECORD_BYTES + 1)

        if len(raw) > MAX_RECORD_BYTES:
            raise ProvenanceValidationError("Provenance record too large")

        record = json.loads(raw.decode("utf-8"))

        validate_provenance(
            record,
            authorized_commit=args.authorized_commit,
            authorized_run_id=args.authorized_run_id,
            authorized_run_attempt=args.authorized_run_attempt,
            expected_version=args.expected_version,
            expected_digest=args.expected_digest,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"PROVENANCE FAILED: Invalid record: {exc}", file=sys.stderr)
        return 1
    except ProvenanceValidationError as exc:
        print(f"PROVENANCE FAILED: {exc}", file=sys.stderr)
        return 1

    print("PROVENANCE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
