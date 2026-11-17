# Runbook: Infrastructure Quality Failure

## Purpose

Diagnose failures in the Infrastructure Quality GitHub Actions job.

## Initial Response

1. Open the failed pull request.
2. Navigate to Checks and select Infrastructure Quality.
3. Identify the first failed step.
4. Read the error message before changing code.
5. Reproduce the failure locally when possible.

Do not disable security checks or remove tests merely to make CI pass.

## Terraform Formatting Failure

**Symptoms:** `terraform fmt -check` exits unsuccessfully.

**Diagnostic commands:**

```bash
terraform fmt -check -recursive infrastructure
terraform fmt -recursive infrastructure
git diff -- infrastructure
```

**Recovery:** Review the formatting changes, rerun validation and commit the corrected configuration.

## Terraform Validation Failure

**Symptoms:** Unsupported block type, invalid resource arguments, missing provider configuration or other Terraform validation errors.

**Diagnostic commands:**

```bash
terraform -chdir=infrastructure init -backend=false
terraform -chdir=infrastructure validate
```

**Recovery:** Correct the reported configuration error. Do not assume that a passing Checkov scan means Terraform is valid.

## TFLint Failure

**Symptoms:** TFLint reports Terraform linting violations.

**Diagnostic command:**

```bash
bash scripts/run-tflint.sh
```

**Recovery:** Identify the relevant rule, understand the violation and correct the Terraform configuration. Rule suppressions require documented justification.

## Checkov Failure

**Symptoms:** Checkov reports one or more failed security policies.

**Diagnostic command:**

```bash
bash scripts/run-checkov.sh
```

**Recovery:** Identify the failed check ID and affected resource. Prefer implementing the security control. Any exception must have a documented reason, scope and review trigger.

Do not use `--soft-fail` to bypass the security gate.

## Python Security Regression Failure

**Diagnostic command:**

```bash
python -m pytest tests/security -v
```

**Recovery:** Determine whether the secure configuration stopped passing, the insecure mutation stopped failing, or Checkov returned an unexpected result.

Do not weaken assertions simply to obtain a passing test.

## Verification

```bash
terraform -chdir=infrastructure validate
bash scripts/run-tflint.sh
bash scripts/run-checkov.sh
python -m pytest tests/security -v
pre-commit run --all-files
```

## Escalation

Escalate to the platform engineering maintainer if the failure cannot be reproduced, the proposed fix weakens a security control, or a tool version change causes unexpected behaviour.

Record the failing step, relevant logs, attempted fixes and final resolution in the pull request.
