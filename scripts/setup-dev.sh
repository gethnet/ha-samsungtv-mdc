#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

PY_BIN="${PY_BIN:-}"
if [ -z "${PY_BIN}" ]; then
  for candidate in python3.14 python3.13 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      PY_BIN="${candidate}"
      break
    fi
  done
fi

if [ -z "${PY_BIN}" ]; then
  echo "No suitable Python found (looked for python3.14/python3.13/python3)." >&2
  exit 1
fi

echo "Using interpreter: ${PY_BIN}"

"${PY_BIN}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "${REPO_DIR}/requirements_test.txt"

echo "Dev env ready. Activate with: source ${VENV_DIR}/bin/activate"
