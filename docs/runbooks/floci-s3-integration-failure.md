# Runbook: Floci S3 Integration Failure

## Purpose

Diagnose failures in the S3 Integration Tests GitHub Actions job.

## Scope

This runbook applies to the local Floci environment and its Terraform-managed S3 resources. It is not an AWS production incident runbook.

## Initial Triage

Identify whether the failure occurred during:

1. Floci container startup
2. S3 API readiness
3. Terraform native tests
4. Terraform plan or apply
5. Python/Boto3 integration tests
6. Terraform destroy or cleanup verification

## Container Startup Failure

**Diagnostic commands:**

```bash
docker ps -a
docker logs floci
docker inspect floci
```

Check for image startup errors, container termination and port binding conflicts.

## S3 API Readiness Failure

**Symptoms:** The readiness loop times out or the S3 API cannot be reached.

**Diagnostic commands:**

```bash
docker ps
docker logs floci

AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=eu-west-2 \
aws --endpoint-url=http://127.0.0.1:4566 \
  s3api list-buckets
```

Verify that Floci is running and listening on the expected endpoint.

## Terraform Provisioning Failure

**Diagnostic commands:**

```bash
terraform -chdir=infrastructure validate
terraform -chdir=infrastructure plan -var="environment=dev"
```

Verify that the local emulator is running before planning or applying.

Review the provider endpoint configuration and the Terraform error output.

## Python Integration Test Failure

**Diagnostic command:**

```bash
python -m pytest tests/integration -v
```

Check the expected bucket name, endpoint configuration, encryption settings, public-access-block configuration and versioning state.

Confirm that Terraform successfully applied the infrastructure before running integration tests.

## Cleanup Failure

The CI workflow attempts to destroy Terraform-managed resources and verifies that no managed resources remain in state.

Inspect the destroy step and Terraform state verification output.

If cleanup fails, preserve the relevant logs and investigate the remaining resources before rerunning the workflow.

Do not manually delete resources or state files without first understanding the failure.

## Verification

A successful recovery requires:

- Floci S3 API readiness
- Successful Terraform native tests
- Successful Terraform plan and apply
- Passing Python integration tests
- Successful Terraform destroy
- Empty Terraform-managed resource list after cleanup

## Escalation

Escalate when emulator behaviour appears inconsistent with expected S3 operations, infrastructure cannot be cleaned up, or a repeated failure cannot be reproduced locally.

Record the failing CI step, container logs, Terraform errors, test results and recovery actions.
