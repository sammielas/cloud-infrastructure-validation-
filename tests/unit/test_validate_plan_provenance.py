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


def test_rejects_substituted_provenance_record(valid_record):
    """A record from a different plan run must not be accepted."""
    attacker_record = {
        **valid_record,
        "source_commit": COMMIT_B,
        "workflow_run_id": "999999999",
        "workflow_run_attempt": "2",
        "plan_sha256": "d" * 64,
    }

    with pytest.raises(
        ProvenanceValidationError,
        match="Unauthorized source commit",
    ):
        verify(attacker_record)


def test_rejects_producer_identity_replaced_by_apply_identity(valid_record):
    """The apply run ID must not replace the authorized producer run ID."""
    apply_run_id = "200"

    attacker_record = {
        **valid_record,
        "workflow_run_id": apply_run_id,
    }

    with pytest.raises(
        ProvenanceValidationError,
        match="Unauthorized workflow run",
    ):
        verify(attacker_record)


def test_matching_attacker_controlled_expectations_are_not_authorization(
    valid_record,
):
    """Demonstrate the trust boundary, not a verifier implementation bug."""
    attacker_record = {
        **valid_record,
        "source_commit": COMMIT_B,
        "workflow_run_id": "999999999",
        "workflow_run_attempt": "2",
        "plan_sha256": "d" * 64,
    }

    # A deliberately unsafe caller obtains every expected value
    # from the same attacker-controlled record.
    #
    # The verifier cannot distinguish these self-consistent values
    # from authentic authorization.
    validate_provenance(
        attacker_record,
        authorized_commit=attacker_record["source_commit"],
        authorized_run_id=attacker_record["workflow_run_id"],
        authorized_run_attempt=attacker_record["workflow_run_attempt"],
        expected_version=attacker_record["terraform_version"],
        expected_digest=attacker_record["plan_sha256"],
    )
