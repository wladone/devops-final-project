#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"
SNAPSHOT_FILE="${VENV_DIR}/.deps.snapshot"
TMP_SNAPSHOT="$(mktemp)"

cleanup() {
  rm -f "${TMP_SNAPSHOT}"
  if [[ -d ".tmp" ]]; then
    find ".tmp" -maxdepth 1 -mindepth 1 \( -name "pip-*" -o -name "tmp*" \) -exec rm -rf {} + 2>/dev/null || true
  fi
}
trap cleanup EXIT

cat requirements.txt requirements-dev.txt > "${TMP_SNAPSHOT}"

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

if [[ ! -f "${SNAPSHOT_FILE}" ]] || ! cmp -s "${TMP_SNAPSHOT}" "${SNAPSHOT_FILE}"; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements-dev.txt
  cp "${TMP_SNAPSHOT}" "${SNAPSHOT_FILE}"
fi
