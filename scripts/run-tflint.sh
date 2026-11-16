#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v tflint >/dev/null 2>&1; then
  echo "ERROR: TFLint is not installed or is missing from PATH."
  exit 1
fi

tflint \
  --config="$ROOT_DIR/.tflint.hcl" \
  --chdir="$ROOT_DIR/infrastructure" \
  --format=compact
