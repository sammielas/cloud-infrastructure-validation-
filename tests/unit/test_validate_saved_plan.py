"""Unit tests for saved Terraform plan integrity validation."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


VALID_COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40
TERRAFORM_VERSION = "1.16.0"

VALIDATOR = Path(__file__).resolve().parents[2] / "scripts" / "validate_saved_plan.py"


@pytest.fixture
def plan_bundle(tmp_path):
    plan = tmp_path / "tfplan"
    metadata = tmp_path / "tfplan.metadata.json"

    plan.write_bytes(b"synthetic-terraform-plan")
    digest = hashlib.sha256(plan.read_bytes()).hexdigest()

    metadata.write_text(
        json.dumps(
            {
                "commit_sha": VALID_COMMIT,
                "terraform_version": TERRAFORM_VERSION,
                "plan_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    return plan, metadata, digest


def run_validator(
    plan, metadata, digest, commit=VALID_COMMIT, version=TERRAFORM_VERSION
):
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--plan",
            str(plan),
            "--metadata",
            str(metadata),
            "--expected-commit",
            commit,
            "--expected-version",
            version,
            "--expected-digest",
            digest,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_plan_passes(plan_bundle):
    plan, metadata, digest = plan_bundle

    result = run_validator(plan, metadata, digest)

    assert result.returncode == 0
    assert "PLAN VALIDATION PASSED" in result.stdout


def test_modified_plan_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle
    plan.write_bytes(b"tampered-terraform-plan")

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "integrity verification failed" in result.stderr


def test_wrong_commit_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle

    result = run_validator(plan, metadata, digest, commit=OTHER_COMMIT)

    assert result.returncode != 0
    assert "commit does not match" in result.stderr


def test_wrong_terraform_version_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle

    result = run_validator(plan, metadata, digest, version="1.15.0")

    assert result.returncode != 0
    assert "Terraform version does not match" in result.stderr


def test_missing_plan_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle
    plan.unlink()

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "does not exist" in result.stderr


def test_modified_metadata_digest_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle
    data = json.loads(metadata.read_text(encoding="utf-8"))
    data["plan_sha256"] = "0" * 64
    metadata.write_text(json.dumps(data), encoding="utf-8")

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "Metadata digest does not match" in result.stderr
