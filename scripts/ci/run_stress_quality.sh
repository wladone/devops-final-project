#!/usr/bin/env bash
set -euo pipefail

SOURCE_FILE="${1:-data/raw/psq_customer_base_v8.csv}"
STRESS_DATA_DIR="${2:-data/stress}"
RULES_FILE="${3:-config/rules.yml}"
OUTPUT_ROOT="${4:-reports/stress}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/bootstrap_python_env.sh"
if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
else
  export PYTHONPATH="$(pwd)/src"
fi

python scripts/data/generate_psq_stress_data.py \
  --source "$SOURCE_FILE" \
  --output-dir "$STRESS_DATA_DIR" \
  --primary-stress-output "data/raw/psq_customer_base_v8_stress.csv"

python scripts/ci/run_stress_matrix.py \
  --data-dir "$STRESS_DATA_DIR" \
  --rules "$RULES_FILE" \
  --output-root "$OUTPUT_ROOT"
