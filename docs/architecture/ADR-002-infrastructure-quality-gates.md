# ADR-002: Enforce Layered Infrastructure Quality Gates

**Status:** Accepted
**Date:** 2026-11-17
**Scope:** Pull-request validation

## Context

Terraform configurations can contain different categories of defects.

A configuration may be correctly formatted but invalid. It may be valid Terraform but violate a security policy. It may pass static analysis but fail when deployed against the local S3 emulator.

No single tool detects all these failure types.

## Decision

Use layered validation in GitHub Actions.

The Infrastructure Quality job performs pre-commit checks, Terraform formatting, Terraform validation, TFLint, Checkov and Python security regression testing.

The S3 Integration Tests job exercises Terraform provisioning and Boto3 interactions against Floci.

Checkov is installed in an isolated Python virtual environment because the pinned scanner version requires a Boto3 version incompatible with the project's integration-test dependencies.

## Alternatives Considered

### Terraform validation only

Insufficient because valid Terraform may still contain insecure or operationally undesirable settings.

### Security scanning only

Insufficient because Checkov does not replace Terraform's configuration and provider-schema validation.

### Integration testing only

Insufficient because deployment success does not demonstrate compliance with static security policies.

## Consequences

### Positive

- Earlier detection of configuration errors
- Automated security-policy enforcement
- Regression protection against insecure public-access settings
- Independent integration testing
- Clearer CI failure categories

### Trade-offs

- Longer CI execution time
- Multiple tools and pinned dependencies require maintenance
- Some checks execute both through pre-commit and explicit workflow steps
- Security exceptions require ongoing review

## Security Exceptions

Checkov suppressions must be narrowly scoped and documented in `docs/security/checkov-exceptions.md`.

A skipped security check is not equivalent to a passed check.

## Review Triggers

Review this decision when adding new infrastructure services, changing security requirements, replacing scanning tools, or introducing real AWS deployment.

## Related Files

- `.pre-commit-config.yaml`
- `.github/workflows/pull-request.yml`
- `.tflint.hcl`
- `requirements-security.txt`
- `scripts/run-tflint.sh`
- `scripts/run-checkov.sh`
- `tests/security/test_checkov_public_access.py`
