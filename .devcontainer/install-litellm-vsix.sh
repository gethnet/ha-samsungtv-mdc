#!/usr/bin/env bash
set -euo pipefail

VSIX_URL="https://github.com/gethnet/litellm-vscode-chat/releases/download/unofficial-0.1.2-dev/litellm-vscode-chat-0.1.2-dev.vsix"

# This script runs inside the dev container after creation.
# It installs the LiteLLM VS Code extension from a VSIX.
#
# Notes:
# - The `code` CLI is typically available in dev containers once VS Code attaches.
# - If it isn't available for some reason, we skip with a clear message.

if ! command -v code >/dev/null 2>&1; then
  echo "[install-litellm-vsix] VS Code CLI 'code' not found in container; skipping VSIX install."
  echo "[install-litellm-vsix] You can still install the VSIX manually via Extensions view."
  exit 0
fi

TMP_DIR="$(mktemp -d)"
VSIX_PATH="$TMP_DIR/litellm-vscode-chat.vsix"

cleanup() {
  rm -rf "$TMP_DIR" || true
}
trap cleanup EXIT

echo "[install-litellm-vsix] Downloading VSIX: $VSIX_URL"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL -o "$VSIX_PATH" "$VSIX_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$VSIX_PATH" "$VSIX_URL"
else
  echo "[install-litellm-vsix] Neither curl nor wget is available; cannot download VSIX."
  exit 1
fi

echo "[install-litellm-vsix] Installing VSIX"
# Use --force to make this idempotent across rebuilds.
code --install-extension "$VSIX_PATH" --force

echo "[install-litellm-vsix] Done"
