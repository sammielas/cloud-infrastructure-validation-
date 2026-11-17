# Operational Runbooks

These runbooks support engineers maintaining the local Terraform infrastructure validation platform.

## Available Runbooks

| Runbook | Purpose |
|---|---|
| [Infrastructure Quality Failure](infrastructure-quality-failure.md) | Diagnose Terraform, TFLint, Checkov and security regression failures |
| [Floci S3 Integration Failure](floci-s3-integration-failure.md) | Diagnose emulator startup, provisioning, integration tests and cleanup failures |

## Runbook Review Checklist

Before approving a new or updated runbook, verify:

- [ ] The failure symptoms are clearly described.
- [ ] Diagnostic commands are valid for the repository.
- [ ] Commands distinguish investigation from remediation.
- [ ] Recovery steps do not unnecessarily weaken security controls.
- [ ] Destructive operations include appropriate safeguards.
- [ ] Verification steps demonstrate successful recovery.
- [ ] Escalation criteria are documented.
- [ ] Instructions match the current GitHub Actions workflow.

## Maintenance

Runbooks should be reviewed whenever the relevant infrastructure, dependencies, security policies or CI workflows change.

Runbooks describe the current local Floci validation environment. They must not be interpreted as production AWS operational procedures.
