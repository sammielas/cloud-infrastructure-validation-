#!/usr/bin/env python3
"""Validate saved Terraform plan metadata before a controlled apply."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class PlanValidationError(Exception):
    """A saved plan failed a required validation check."""


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 over the exact bytes of a saved plan."""
    digest = hashlib.sha256()

    with path.open("rb") as plan_file:
        for chunk in iter(lambda: plan_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_saved_plan(
    plan_path: Path,
    metadata_path: Path,
    expected_commit: str,
    expected_version: str,
    expected_digest: str,
) -> None:
    """Reject missing, modified or incorrectly identified plans."""

    if not plan_path.is_file():
        raise PlanValidationError("Saved plan file does not exist")

    if not metadata_path.is_file():
        raise PlanValidationError("Plan metadata file does not exist")

    if not COMMIT_PATTERN.fullmatch(expected_commit):
        raise PlanValidationError("Expected commit must be a full Git SHA")

    if not SHA256_PATTERN.fullmatch(expected_digest):
        raise PlanValidationError("Expected digest must be a SHA-256 hex value")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlanValidationError("Cannot read valid plan metadata") from exc

    if not isinstance(metadata, dict):
        raise PlanValidationError("Plan metadata must be a JSON object")

    if metadata.get("commit_sha") != expected_commit:
        raise PlanValidationError("Plan commit does not match expected commit")

    if metadata.get("terraform_version") != expected_version:
        raise PlanValidationError("Terraform version does not match")

    if metadata.get("plan_sha256") != expected_digest:
        raise PlanValidationError("Metadata digest does not match trusted digest")

    try:
        actual_digest = sha256_file(plan_path)
    except OSError as exc:
        raise PlanValidationError("Cannot read saved plan file") from exc

    if actual_digest != expected_digest:
        raise PlanValidationError("Saved plan integrity verification failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a saved Terraform plan before apply."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-digest", required=True)

    args = parser.parse_args()

    try:
        validate_saved_plan(
            plan_path=args.plan,
            metadata_path=args.metadata,
            expected_commit=args.expected_commit,
            expected_version=args.expected_version,
            expected_digest=args.expected_digest,
        )
    except PlanValidationError as exc:
        print(f"PLAN VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("PLAN VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
