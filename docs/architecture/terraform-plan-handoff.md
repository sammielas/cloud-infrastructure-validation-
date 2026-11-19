# Terraform Saved-Plan Handoff: Trust Boundaries

Status: Proposed
Work item: PLAT-148

## Objective

Ensure that a reviewed Terraform plan cannot be replaced with a
different plan without the apply process detecting the substitution.

## Scope

This design initially targets an isolated Floci-based validation
environment. It does not authorize production AWS deployments.

## Trust boundaries

### Untrusted artifact bundle

The plan bundle contains:

- tfplan
- tfplan.metadata.json

Both files are treated as potentially replaceable.

### Trusted provenance record

A separately protected record must bind:

- The plan SHA-256 digest
- The exact source commit SHA
- The producing workflow run and attempt
- The Terraform version
- The artifact identity

The apply process must authenticate the origin and integrity of this
record independently of the artifact bundle.

### Approval boundary

Approval must refer to the specific plan and provenance record.

An approval of a branch name alone is insufficient because the
branch can advance after approval.

### Apply boundary

Before applying, the system must:

1. Verify the provenance record's trusted origin.
2. Verify the source commit and workflow identity.
3. Compare the downloaded plan digest with the trusted digest.
4. Compare metadata fields with the trusted record.
5. Confirm that approval covers the verified plan.
6. Ensure the validated bytes cannot be replaced before apply.
7. Allow Terraform to reject a stale plan against current state.

## Explicit non-goals

- Production AWS deployment
- Real AWS IAM authorization testing
- Automatic deployment from pull requests
- Assuming that a checksum inside an artifact is authoritative

## Open design decisions

- Where will the protected provenance record live?
- How will the apply job authenticate its producer?
- How will approval be bound to an exact plan?
- How will the validated plan be protected until apply?
- How will a failed apply preserve evidence and clean up safely?
