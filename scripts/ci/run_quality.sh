#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-data/raw/psq_customer_base_v8_stress.csv}"
RULES_FILE="${2:-config/rules.yml}"
OUTPUT_DIR="${3:-reports/ci}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/bootstrap_python_env.sh"
python src/main.py --input "$INPUT_FILE" --rules "$RULES_FILE" --output-dir "$OUTPUT_DIR"
