#!/usr/bin/env bash
set -euo pipefail

# Run from repo root regardless of where called from
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Running hassfest (Home Assistant) validation..."
docker run --rm --platform linux/amd64 \
  -v "$PWD:/github/workspace" -w /github/workspace \
  ghcr.io/home-assistant/hassfest:latest \
  --integration-path /github/workspace/custom_components/samsungtv_mdc

echo "==> Running ruff (integration only, ignoring site-packages/venv)..."
docker run --rm \
  -v "$ROOT_DIR:/workspace" \
  -w /workspace \
  ghcr.io/astral-sh/ruff:latest \
  check custom_components/samsungtv_mdc \
  --extend-exclude '**/site-packages/**' \
  --extend-exclude '.venv'

echo "==> Running HACS validation..."
docker run --rm \
  --platform linux/amd64 \
  -v "$ROOT_DIR:/workspace" \
  -w /workspace \
  ghcr.io/hacs/action:22.5.0 \
  python -m hacs_action \
    --category integration \
    --ignore brands \
  | grep -vE "site-packages|\\.(venv|env)/"

echo "All validations passed."
