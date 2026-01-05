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

echo "==> Running HACS validation..."
docker run --rm \
  --platform linux/amd64 \
  -v "$ROOT_DIR:/workspace" \
  -w /workspace \
  ghcr.io/hacs/action:22.5.0 \
  python -m hacs_action \
    --category integration \
    --ignore brands

echo "All validations passed."