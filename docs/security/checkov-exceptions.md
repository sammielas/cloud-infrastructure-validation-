# Checkov Security Exceptions

## Purpose

This document records security controls intentionally deferred in the local Floci-based Terraform infrastructure validation environment.

These exceptions apply only to the local S3 infrastructure configuration. They are not approved exceptions for production AWS environments.

## Current Security Baseline

The Terraform-managed S3 bucket implements:

- S3 public-access blocking
- Server-side encryption using SSE-S3 (AES256)
- S3 bucket versioning
- Terraform configuration validation
- TFLint static analysis
- Checkov security scanning

**Validated Checkov baseline:** 11 passed, 0 failed, 5 skipped.

## Documented Exceptions

### CKV_AWS_144: Cross-region replication

**Reason:** The current infrastructure runs exclusively against the local Floci emulator. Multi-region replication is outside the scope of this environment.

**Review trigger:** Introduction of real AWS environments or disaster-recovery requirements.

### CKV2_AWS_61: S3 lifecycle configuration

**Reason:** An artifact retention and expiration policy has not yet been defined.

**Review trigger:** Establishment of artifact retention requirements.

### CKV_AWS_18: S3 access logging

**Reason:** The current local environment does not include a centralized S3 access logging architecture.

**Review trigger:** Introduction of centralized logging or real AWS deployment.

### CKV2_AWS_62: S3 event notifications

**Reason:** No downstream event consumer currently requires S3 event notifications.

**Review trigger:** Introduction of event-driven workflows or integrations.

### CKV_AWS_145: KMS encryption

**Reason:** SSE-S3 (AES256) is the encryption baseline selected for the local emulator environment. Customer-managed KMS encryption has not been implemented.

**Review trigger:** Real AWS security architecture review or requirements for customer-managed encryption keys.

## Ownership and Review

**Proposed owner:** Platform Engineering

**Approval status:** Documented for local development; no formal production security approval.

All exceptions must be reviewed before deploying equivalent infrastructure to a real AWS environment.

Exceptions must be removed when the corresponding security control becomes applicable and has been implemented.

## Security Regression Testing

The repository includes an automated Python security regression test:

`tests/security/test_checkov_public_access.py`

The test verifies that:

1. Checkov accepts the secure S3 public-access configuration.
2. Checkov rejects an intentionally insecure configuration.
3. The original Terraform infrastructure files remain unchanged.

Security scanning is integrated into pre-commit and the Infrastructure Quality GitHub Actions job.

## Validation Commands

```bash
bash scripts/run-checkov.sh
python -m pytest tests/security -v
pre-commit run --all-files
```

A successful scan with skipped checks does not mean those checks passed. The five exceptions remain outstanding until their requirements are addressed.
