#!/usr/bin/env bash
set -euo pipefail

# Run from repo root regardless of where called from
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
CONTAINER_WORKSPACE="/home/runner/work/ha-samsungtv-mdc/ha-samsungtv-mdc"

STATUS=0

echo "==> Running hassfest validation..."
if ! docker run --rm --platform linux/amd64 \
  -v "$ROOT_DIR:$CONTAINER_WORKSPACE" \
  -w "$CONTAINER_WORKSPACE" \
  ghcr.io/home-assistant/hassfest:latest \
  --integration-path "$CONTAINER_WORKSPACE/custom_components/samsungtv_mdc"
then
  STATUS=1
fi

echo "==> Running HACS validation..."
set +o pipefail
if ! docker run --rm \
    --platform linux/amd64 \
    -v "$ROOT_DIR:/workspace" \
    -w /workspace \
    ghcr.io/hacs/action:main \
    python -m hacs_action \
      --category integration \
      --ignore brands \
    | grep -vE "site-packages|\\.(venv|env)/"
then
  STATUS=1
fi
set -o pipefail

if [ "$STATUS" -ne 0 ]; then
  echo "One or more validation steps failed."
  exit "$STATUS"
fi

echo "All validations passed."
