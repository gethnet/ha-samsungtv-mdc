#!/usr/bin/env bash
set -euo pipefail

# Run from repo root regardless of where called from
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STATUS=0

echo "==> Running hassfest (Home Assistant) validation..."
if ! docker run --rm --platform linux/amd64 \
  -v "$PWD:/github/workspace" -w /github/workspace \
  ghcr.io/home-assistant/hassfest:latest \
  --integration-path /github/workspace/custom_components/samsungtv_mdc
then
  STATUS=1
fi

echo "==> Running ruff (integration only, ignoring site-packages/venv)..."
if ! docker run --rm \
  -v "$ROOT_DIR:/workspace" \
  -w /workspace \
  ghcr.io/astral-sh/ruff:latest \
  check custom_components/samsungtv_mdc \
  --extend-exclude '**/site-packages/**' \
  --extend-exclude '.venv'
then
  STATUS=1
fi

echo "==> Running HACS validation..."
set +o pipefail
if ! docker run --rm \
    --platform linux/amd64 \
    -v "$ROOT_DIR:/workspace" \
    -w /workspace \
    ghcr.io/hacs/action:22.5.0 \
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
