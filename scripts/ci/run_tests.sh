#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/bootstrap_python_env.sh"

python -m pytest \
  --cov=src \
  --cov=dashboard \
  --cov-report=xml:coverage.xml

if [[ -d ".tmp" ]]; then
  find ".tmp" -maxdepth 1 -mindepth 1 \( -name "pip-*" -o -name "tmp*" \) -exec rm -rf {} + 2>/dev/null || true
fi
