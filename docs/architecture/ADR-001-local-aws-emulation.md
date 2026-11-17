# ADR-001: Use Floci for Local AWS Infrastructure Validation

**Status:** Accepted for the current local validation architecture
**Date:** 2026-11-17
**Scope:** Terraform-managed S3 infrastructure

## Context

The platform engineering repository requires a repeatable environment for validating Terraform-managed AWS S3 resources without provisioning resources in a real AWS account.

The current infrastructure provisions an application artifacts bucket, public-access protection, server-side encryption and versioning.

Developers need to exercise infrastructure provisioning and Python/Boto3 integration tests in both local development and GitHub Actions.

## Decision

Use Floci as the local AWS-compatible S3 emulator.

Configure Terraform's AWS provider to use the local S3 endpoint and test-only credentials. Run the emulator in a Docker container during integration tests.

Use a pinned container image digest in GitHub Actions to reduce unexpected changes to the test environment.

## Alternatives Considered

### Real AWS development account

Advantages:
- Tests actual AWS service behaviour
- Supports AWS-specific features and IAM validation

Disadvantages:
- Requires credentials and account management
- Introduces infrastructure costs
- Increases cleanup and access-control requirements

### Mock-only unit testing

Advantages:
- Fast execution
- Minimal infrastructure dependencies

Disadvantages:
- Cannot fully exercise Terraform provisioning and S3 API interactions

## Consequences

### Positive

- Repeatable infrastructure integration testing
- No real AWS credentials required
- Local and CI environments can exercise the same S3 workflow
- Reduced risk of accidentally provisioning paid cloud resources

### Limitations

- Emulator behaviour may differ from real AWS
- AWS IAM, KMS, cross-region replication and other service integrations are not fully validated
- Passing emulator tests does not establish production readiness

## Review Triggers

Revisit this decision when real AWS deployment is introduced, emulator compatibility becomes insufficient, or the platform requires services beyond the current local test scope.

## Related Files

- `infrastructure/provider.tf`
- `infrastructure/storage.tf`
- `.github/workflows/pull-request.yml`
- `tests/integration/test_s3_storage.py`
