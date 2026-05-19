#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-data/raw/psq_customer_base_v8_stress.csv}"
RULES_FILE="${2:-config/rules.yml}"
DATA_OUTPUT_DIR="${3:-data/processed/quality_ladder}"
REPORT_OUTPUT_ROOT="${4:-reports/quality-ladder}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/bootstrap_python_env.sh"
if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
else
  export PYTHONPATH="$(pwd)/src"
fi

python scripts/data/generate_psq_quality_ladder.py \
  --input "$INPUT_FILE" \
  --rules "$RULES_FILE" \
  --data-output-dir "$DATA_OUTPUT_DIR" \
  --report-output-root "$REPORT_OUTPUT_ROOT"
