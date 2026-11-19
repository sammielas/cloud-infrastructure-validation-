"""Regression tests for Terraform saved-plan state freshness."""

import json

import subprocess
from pathlib import Path

import pytest


TERRAFORM_CONFIG = """
terraform {
  required_version = "= 1.16.0"
}

resource "terraform_data" "example" {
  input = "original"
}
"""


def run_terraform(directory: Path, *arguments: str):
    """Execute Terraform against an isolated working directory."""
    return subprocess.run(
        ["terraform", f"-chdir={directory}", *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@pytest.mark.integration
def test_stale_saved_plan_is_rejected(tmp_path):
    """Reject Plan A after another operation changes Terraform state."""

    configuration = tmp_path / "main.tf"
    configuration.write_text(TERRAFORM_CONFIG, encoding="utf-8")

    # Initialize the isolated Terraform configuration.
    init = run_terraform(tmp_path, "init", "-input=false", "-no-color")
    assert init.returncode == 0, init.stderr

    # Generate Plan A, but do not apply it.
    plan_a = run_terraform(
        tmp_path,
        "plan",
        "-input=false",
        "-no-color",
        "-out=plan-a.tfplan",
    )
    assert plan_a.returncode == 0, plan_a.stderr
    assert (tmp_path / "plan-a.tfplan").is_file()

    # Change configuration and apply a different operation.
    configuration.write_text(
        TERRAFORM_CONFIG.replace(
            'input = "original"',
            'input = "changed"',
        ),
        encoding="utf-8",
    )

    apply_b = run_terraform(
        tmp_path,
        "apply",
        "-input=false",
        "-auto-approve",
        "-no-color",
    )
    assert apply_b.returncode == 0, apply_b.stderr

    # Verify that Terraform actually recorded the new resource.
    state = run_terraform(tmp_path, "state", "list")
    assert state.returncode == 0, state.stderr
    assert "terraform_data.example" in state.stdout

    # Confirm the intervening apply recorded the intended state.
    state_json = run_terraform(
        tmp_path,
        "show",
        "-json",
    )
    assert state_json.returncode == 0, state_json.stderr

    state_data = json.loads(state_json.stdout)
    resources = state_data["values"]["root_module"]["resources"]

    resource = next(
        item for item in resources if item["address"] == "terraform_data.example"
    )

    assert resource["values"]["input"] == "changed"

    # Attempt to apply the original saved Plan A.
    stale_apply = run_terraform(
        tmp_path,
        "apply",
        "-input=false",
        "-no-color",
        "plan-a.tfplan",
    )

    assert stale_apply.returncode != 0, (
        "Terraform unexpectedly accepted a stale saved plan"
    )

    assert "Saved plan is stale" in stale_apply.stderr, (
        "Terraform failed, but not for the expected stale-plan reason.\n"
        f"stdout:\n{stale_apply.stdout}\n"
        f"stderr:\n{stale_apply.stderr}"
    )
