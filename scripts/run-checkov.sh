
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -x "$ROOT_DIR/.venv-checkov/bin/checkov" ]; then
  CHECKOV="$ROOT_DIR/.venv-checkov/bin/checkov"
elif command -v checkov >/dev/null 2>&1; then
  CHECKOV="$(command -v checkov)"
else
  echo "ERROR: Checkov is not installed or is missing from PATH." >&2
  exit 1
fi

cd "$ROOT_DIR"

"$CHECKOV" \
  --directory infrastructure \
  --framework terraform \
  --skip-path 'infrastructure/tests/.*' \
  --output cli \
  --quiet
