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

## Execution boundary and TOCTOU

A successful digest verification does not guarantee that the same
bytes will subsequently be consumed by Terraform.

The apply environment must prevent untrusted processes from
modifying or replacing the plan between verification and execution.

Required controls:

- Use an isolated apply execution environment.
- Do not execute untrusted repository scripts after validation.
- Do not expose the verified plan directory to untrusted writers.
- Restrict file and directory modification permissions.
- Do not treat chmod alone as a complete security boundary.
- Revalidate deployment authorization immediately before apply.
- Fail closed if any required control cannot be established.

The local filesystem demonstration illustrates the risk but does
not prove production-grade runner isolation.

## Authenticated CI handoff design

### Producer

The plan-producing workflow must execute trusted workflow code.

It must record the exact source commit, workflow run ID,
workflow run attempt, Terraform version and plan digest.

The saved plan must have a verifiable artifact attestation.

### Transport

Downloaded plans and accompanying metadata are untrusted until
the consumer verifies their integrity and provenance.

### Approval

The deployment environment must enforce required reviewers
where supported and configured.

Approval must be associated with the exact authorized plan
digest and producer identity. Environment approval alone is
not evidence of digest-specific approval.

### Consumer

The apply workflow must:

1. Authenticate the artifact attestation.
2. Verify the expected repository and producer workflow.
3. Verify the authorized source commit and producer run.
4. Verify the plan digest against trusted provenance.
5. Verify the release authorization for that exact plan.
6. Confirm the authorized source revision remains eligible.
7. Protect the plan from modification until Terraform consumes it.
8. Fail closed on any mismatch.

### State continuity

A cross-job saved-plan apply requires compatible Terraform state
and the same intended infrastructure environment.

An independently started Floci instance does not automatically
preserve the producer's Terraform state or resources.

### Current implementation status

Provenance identity and digest checks have local regression tests.

Signed attestation verification, digest-specific approval,
state continuity and isolated apply execution remain unimplemented.

## Authenticated CI handoff design

### Producer

The plan-producing workflow must execute trusted workflow code.

It must record the exact source commit, workflow run ID,
workflow run attempt, Terraform version and plan digest.

The saved plan must have a verifiable artifact attestation.

### Transport

Downloaded plans and accompanying metadata are untrusted until
the consumer verifies their integrity and provenance.

### Approval

The deployment environment must enforce required reviewers
where supported and configured.

Approval must be associated with the exact authorized plan
digest and producer identity. Environment approval alone is
not evidence of digest-specific approval.

### Consumer

The apply workflow must:

1. Authenticate the artifact attestation.
2. Verify the expected repository and producer workflow.
3. Verify the authorized source commit and producer run.
4. Verify the plan digest against trusted provenance.
5. Verify the release authorization for that exact plan.
6. Confirm the authorized source revision remains eligible.
7. Protect the plan from modification until Terraform consumes it.
8. Fail closed on any mismatch.

### State continuity

A cross-job saved-plan apply requires compatible Terraform state
and the same intended infrastructure environment.

An independently started Floci instance does not automatically
preserve the producer's Terraform state or resources.

### Current implementation status

Provenance identity and digest checks have local regression tests.

Signed attestation verification, digest-specific approval,
state continuity and isolated apply execution remain unimplemented.
