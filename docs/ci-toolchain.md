# CI Toolchain

This document records the tool versions used by the
infrastructure validation pipeline.

| Tool | Version |
|------|---------|
| Python | 3.10.12 |
| Terraform | 1.16.0 |
| pre-commit | 4.3.0 |

GitHub Actions are pinned to full commit SHAs.

## Validation

Changes to tool versions must be tested locally and
validated through the pull request pipeline before merging.

## Maintenance

Tool versions and GitHub Actions references should be
reviewed periodically for security updates and compatibility.
