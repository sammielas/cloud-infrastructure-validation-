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
    plan,
    metadata,
    digest,
    commit=VALID_COMMIT,
    version=TERRAFORM_VERSION,
    artifact_dir=None,
):
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--artifact-dir",
            str(artifact_dir if artifact_dir is not None else metadata.parent),
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
    assert "Cannot safely read expected artifact" in result.stderr


def test_modified_metadata_digest_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle
    data = json.loads(metadata.read_text(encoding="utf-8"))
    data["plan_sha256"] = "0" * 64
    metadata.write_text(json.dumps(data), encoding="utf-8")

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "Metadata digest does not match" in result.stderr


def test_plan_path_traversal_is_rejected(plan_bundle, tmp_path):
    plan, metadata, digest = plan_bundle

    outside = tmp_path.parent / "outside" / "tfplan"
    result = run_validator(outside, metadata, digest, artifact_dir=tmp_path)

    assert result.returncode != 0
    assert "outside the trusted directory" in result.stderr


def test_metadata_path_traversal_is_rejected(plan_bundle, tmp_path):
    plan, metadata, digest = plan_bundle

    outside = tmp_path.parent / "outside" / "tfplan.metadata.json"
    result = run_validator(plan, outside, digest, artifact_dir=tmp_path)

    assert result.returncode != 0
    assert "outside the trusted directory" in result.stderr


def test_plan_symlink_is_rejected(plan_bundle, tmp_path):
    plan, metadata, digest = plan_bundle

    outside = tmp_path / "outside-plan"
    outside.write_bytes(plan.read_bytes())

    plan.unlink()
    plan.symlink_to(outside)

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "symlinks are not permitted" in result.stderr


def test_metadata_symlink_is_rejected(plan_bundle, tmp_path):
    plan, metadata, digest = plan_bundle

    outside = tmp_path / "outside-metadata.json"
    outside.write_bytes(metadata.read_bytes())

    metadata.unlink()
    metadata.symlink_to(outside)

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "symlinks are not permitted" in result.stderr


def test_relative_plan_traversal_is_rejected(plan_bundle, tmp_path):
    plan, metadata, digest = plan_bundle

    result = run_validator(
        Path("..") / "outside" / "tfplan",
        metadata,
        digest,
        artifact_dir=tmp_path,
    )

    assert result.returncode != 0
    assert "outside the trusted directory" in result.stderr


def test_unexpected_plan_filename_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle

    result = run_validator(
        plan.with_name("unexpected.tfplan"),
        metadata,
        digest,
    )

    assert result.returncode != 0
    assert "Unexpected artifact filename" in result.stderr


def test_symlinked_artifact_directory_is_rejected(plan_bundle, tmp_path):
    plan, metadata, digest = plan_bundle

    linked_dir = tmp_path.parent / f"{tmp_path.name}-link"
    linked_dir.symlink_to(tmp_path, target_is_directory=True)

    result = run_validator(
        plan,
        metadata,
        digest,
        artifact_dir=linked_dir,
    )

    assert result.returncode != 0
    assert "Trusted artifact directory is invalid" in result.stderr


def test_non_regular_plan_is_rejected(plan_bundle):
    plan, metadata, digest = plan_bundle

    plan.unlink()
    plan.mkdir()

    result = run_validator(plan, metadata, digest)

    assert result.returncode != 0
    assert "Artifact is not a regular file" in result.stderr
