#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/devops_tooling.sh"

ENVIRONMENTS="${1:-dev staging prod}"

read -r -a ENV_ARRAY <<< "$ENVIRONMENTS"

for ENV_NAME in "${ENV_ARRAY[@]}"; do
  ENV_DIR="terraform/environments/${ENV_NAME}"
  if [[ ! -d "${ENV_DIR}" ]]; then
    echo "Terraform environment directory not found: ${ENV_DIR}" >&2
    exit 1
  fi

  echo "Validating Terraform environment: ${ENV_NAME}"
  TF_DATA_DIR="$(pwd)/.tmp/terraform/${ENV_NAME}" run_terraform -chdir="${ENV_DIR}" init -backend=false
  TF_DATA_DIR="$(pwd)/.tmp/terraform/${ENV_NAME}" run_terraform -chdir="${ENV_DIR}" validate
done
