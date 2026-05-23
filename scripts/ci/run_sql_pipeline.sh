#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-data/raw/psq_customer_base_v8.csv}"
DB_PATH="${2:-data/db/dq.db}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/bootstrap_python_env.sh"

export DQ_DATABASE_URL="sqlite:///${DB_PATH}"

# Reset on every CI run so we always reflect the current input deterministically.
python scripts/data/run_sql_pipeline.py --input "$INPUT_FILE" --reset
