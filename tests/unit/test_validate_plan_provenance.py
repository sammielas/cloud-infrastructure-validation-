"""Security regression tests for Terraform plan provenance."""

import pytest

from scripts.validate_plan_provenance import (
    ProvenanceValidationError,
    validate_provenance,
)

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
DIGEST = "c" * 64


@pytest.fixture
def valid_record():
    return {
        "source_commit": COMMIT_A,
        "workflow_run_id": "123456789",
        "workflow_run_attempt": "1",
        "terraform_version": "1.16.0",
        "plan_sha256": DIGEST,
    }


def verify(record, **overrides):
    expected = {
        "authorized_commit": COMMIT_A,
        "authorized_run_id": "123456789",
        "authorized_run_attempt": "1",
        "expected_version": "1.16.0",
        "expected_digest": DIGEST,
    }
    expected.update(overrides)
    validate_provenance(record, **expected)


def test_accepts_authorized_plan(valid_record):
    verify(valid_record)


def test_rejects_old_commit_even_with_valid_digest(valid_record):
    with pytest.raises(
        ProvenanceValidationError,
        match="Unauthorized source commit",
    ):
        verify(valid_record, authorized_commit=COMMIT_B)


def test_rejects_different_workflow_run(valid_record):
    with pytest.raises(
        ProvenanceValidationError,
        match="Unauthorized workflow run",
    ):
        verify(valid_record, authorized_run_id="987654321")


def test_rejects_different_workflow_attempt(valid_record):
    with pytest.raises(
        ProvenanceValidationError,
        match="Unauthorized workflow attempt",
    ):
        verify(valid_record, authorized_run_attempt="2")


def test_rejects_changed_digest(valid_record):
    valid_record["plan_sha256"] = "d" * 64
    with pytest.raises(
        ProvenanceValidationError,
        match="Trusted plan digest mismatch",
    ):
        verify(valid_record)


def test_rejects_wrong_terraform_version(valid_record):
    with pytest.raises(
        ProvenanceValidationError,
        match="Terraform version mismatch",
    ):
        verify(valid_record, expected_version="1.15.0")


def test_rejects_extra_provenance_fields(valid_record):
    valid_record["approved"] = "true"
    with pytest.raises(
        ProvenanceValidationError,
        match="Unexpected provenance fields",
    ):
        verify(valid_record)


def test_rejects_invalid_authorized_commit(valid_record):
    with pytest.raises(
        ProvenanceValidationError,
        match="Invalid authorized commit",
    ):
        verify(valid_record, authorized_commit="main")


def test_rejects_non_string_record_field(valid_record):
    valid_record["workflow_run_id"] = 123456789
    with pytest.raises(
        ProvenanceValidationError,
        match="Invalid field type",
    ):
        verify(valid_record)


def test_rejects_zero_run_id(valid_record):
    with pytest.raises(
        ProvenanceValidationError,
        match="Invalid authorized run ID",
    ):
        verify(valid_record, authorized_run_id="0")


def test_cli_rejects_malformed_json(tmp_path):
    import subprocess
    import sys

    record_path = tmp_path / "provenance.json"
    record_path.write_text("{invalid-json", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_plan_provenance.py",
            "--record",
            str(record_path),
            "--authorized-commit",
            COMMIT_A,
            "--authorized-run-id",
            "123456789",
            "--authorized-run-attempt",
            "1",
            "--expected-version",
            "1.16.0",
            "--expected-digest",
            DIGEST,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "PROVENANCE FAILED" in result.stderr


def test_cli_rejects_oversized_record(tmp_path):
    import subprocess
    import sys

    record_path = tmp_path / "provenance.json"
    record_path.write_bytes(b"x" * (64 * 1024 + 1))

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_plan_provenance.py",
            "--record",
            str(record_path),
            "--authorized-commit",
            COMMIT_A,
            "--authorized-run-id",
            "123456789",
            "--authorized-run-attempt",
            "1",
            "--expected-version",
            "1.16.0",
            "--expected-digest",
            DIGEST,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Provenance record too large" in result.stderr
