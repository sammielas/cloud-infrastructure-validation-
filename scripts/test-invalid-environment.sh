#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/infrastructure"

EXPECTED_ERROR="Environment must be dev, test, or staging."

OUTPUT_FILE="$(mktemp)"
trap 'rm -f "$OUTPUT_FILE"' EXIT

echo "Testing Terraform variable validation..."

if terraform -chdir="$TF_DIR" plan \
  -input=false \
  -no-color \
  -var="environment=production" \
  >"$OUTPUT_FILE" 2>&1; then

  echo "FAIL: Terraform accepted an invalid environment."
  exit 1
fi

if ! grep -Fq "$EXPECTED_ERROR" "$OUTPUT_FILE"; then
  echo "FAIL: Terraform failed for an unexpected reason."
  cat "$OUTPUT_FILE"
  exit 1
fi

echo "PASS: Invalid environment rejected as expected."
