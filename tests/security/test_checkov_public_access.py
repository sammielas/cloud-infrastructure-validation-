"""Ensure Checkov rejects insecure S3 public-access configuration."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORAGE_FILE = ROOT / "infrastructure" / "storage.tf"

CHECK_ID = "CKV_AWS_53"


def get_checkov_executable() -> str:
    """Find the isolated Checkov executable or a PATH installation."""
    local_checkov = ROOT / ".venv-checkov" / "bin" / "checkov"

    if local_checkov.is_file():
        return str(local_checkov)

    executable = shutil.which("checkov")
    assert executable is not None, "Checkov executable not found"
    return executable


def run_checkov(terraform_file: Path) -> tuple[int, dict]:
    """Run a targeted Checkov scan and return its exit code and report."""
    result = subprocess.run(
        [
            get_checkov_executable(),
            "--file",
            str(terraform_file),
            "--framework",
            "terraform",
            "--check",
            CHECK_ID,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.stdout.strip(), f"Checkov returned no JSON output: {result.stderr}"

    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    assert not report.get("parsing_errors")

    return result.returncode, report


def test_public_access_security_regression(tmp_path: Path) -> None:
    """Verify secure settings pass and insecure settings fail."""
    original = STORAGE_FILE.read_text(encoding="utf-8")

    secure_line = "block_public_acls       = true"
    insecure_line = "block_public_acls       = false"

    assert original.count(secure_line) == 1

    secure_file = tmp_path / "secure.tf"
    secure_file.write_text(original, encoding="utf-8")

    secure_code, secure_report = run_checkov(secure_file)

    assert secure_code == 0
    assert any(
        check["check_id"] == CHECK_ID
        for check in secure_report["results"]["passed_checks"]
    )

    insecure_file = tmp_path / "insecure.tf"
    insecure_file.write_text(
        original.replace(secure_line, insecure_line, 1),
        encoding="utf-8",
    )

    insecure_code, insecure_report = run_checkov(insecure_file)

    assert insecure_code != 0
    assert any(
        check["check_id"] == CHECK_ID
        and check["resource"].endswith(
            "aws_s3_bucket_public_access_block.application_artifacts"
        )
        for check in insecure_report["results"]["failed_checks"]
    )
