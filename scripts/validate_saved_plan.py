#!/usr/bin/env python3
"""Validate saved Terraform plan metadata before a controlled apply."""

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")

PLAN_FILENAME = "tfplan"
METADATA_FILENAME = "tfplan.metadata.json"
INVALID_ARTIFACT_DIRECTORY_MESSAGE = "Trusted artifact directory is invalid"

MAX_METADATA_BYTES = 64 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


class PlanValidationError(Exception):
    """A saved plan failed a required validation check."""


def validate_artifact_path(
    supplied_path: Path,
    trusted_dir: Path,
    required_filename: str,
) -> None:
    """Require an exact filename directly inside the trusted directory."""
    if supplied_path.name != required_filename:
        raise PlanValidationError("Unexpected artifact filename")

    candidate = (
        supplied_path if supplied_path.is_absolute() else Path.cwd() / supplied_path
    )

    if candidate.parent != trusted_dir:
        raise PlanValidationError("Artifact path is outside the trusted directory")


def open_artifact(directory_fd: int, filename: str):
    """Open a regular artifact without following a final-component symlink."""
    if filename not in {PLAN_FILENAME, METADATA_FILENAME}:
        raise PlanValidationError("Unexpected artifact filename")

    try:
        file_fd = os.open(
            filename,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
    except OSError as exc:
        raise PlanValidationError("Cannot safely read expected artifact") from exc

    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise PlanValidationError("Artifact is not a regular file")

        return os.fdopen(file_fd, "rb")
    except BaseException:
        os.close(file_fd)
        raise


def read_metadata(directory_fd: int) -> dict:
    """Read bounded JSON metadata from the trusted directory."""
    with open_artifact(directory_fd, METADATA_FILENAME) as metadata_file:
        data = metadata_file.read(MAX_METADATA_BYTES + 1)

    if len(data) > MAX_METADATA_BYTES:
        raise PlanValidationError("Plan metadata exceeds size limit")

    try:
        metadata = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PlanValidationError("Cannot read valid plan metadata") from exc

    if not isinstance(metadata, dict):
        raise PlanValidationError("Plan metadata must be a JSON object")

    return metadata


def sha256_plan(directory_fd: int) -> str:
    """Hash a saved plan in bounded chunks."""
    digest = hashlib.sha256()

    with open_artifact(directory_fd, PLAN_FILENAME) as plan_file:
        for chunk in iter(
            lambda: plan_file.read(HASH_CHUNK_BYTES),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_saved_plan(
    artifact_dir: Path,
    plan_path: Path,
    metadata_path: Path,
    expected_commit: str,
    expected_version: str,
    expected_digest: str,
) -> None:
    """Reject untrusted paths, modified plans and incorrect metadata."""
    if not COMMIT_PATTERN.fullmatch(expected_commit):
        raise PlanValidationError("Expected commit must be a full Git SHA")

    if not SHA256_PATTERN.fullmatch(expected_digest):
        raise PlanValidationError("Expected digest must be a SHA-256 hex value")

    if artifact_dir.is_symlink():
        raise PlanValidationError(INVALID_ARTIFACT_DIRECTORY_MESSAGE)

    try:
        trusted_dir = artifact_dir.resolve(strict=True)

        directory_fd = os.open(
            trusted_dir,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except OSError as exc:
        raise PlanValidationError(INVALID_ARTIFACT_DIRECTORY_MESSAGE) from exc

    try:
        if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
            raise PlanValidationError(INVALID_ARTIFACT_DIRECTORY_MESSAGE)

        validate_artifact_path(plan_path, trusted_dir, PLAN_FILENAME)
        validate_artifact_path(metadata_path, trusted_dir, METADATA_FILENAME)

        for path in (plan_path, metadata_path):
            if path.is_symlink():
                raise PlanValidationError("Artifact symlinks are not permitted")

        metadata = read_metadata(directory_fd)

        if metadata.get("commit_sha") != expected_commit:
            raise PlanValidationError("Plan commit does not match expected commit")

        if metadata.get("terraform_version") != expected_version:
            raise PlanValidationError("Terraform version does not match")

        if metadata.get("plan_sha256") != expected_digest:
            raise PlanValidationError("Metadata digest does not match trusted digest")

        actual_digest = sha256_plan(directory_fd)

        if actual_digest != expected_digest:
            raise PlanValidationError("Saved plan integrity verification failed")
    except OSError as exc:
        raise PlanValidationError("Cannot safely read expected artifact") from exc
    finally:
        os.close(directory_fd)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a saved Terraform plan before apply."
    )
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-digest", required=True)

    args = parser.parse_args()

    try:
        validate_saved_plan(
            artifact_dir=args.artifact_dir,
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
