#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-dev}"
RELEASE_NAME="${2:-data-quality-monitor}"
NAMESPACE="${3:-dq-monitor-${ENVIRONMENT}}"
VALUES_FILE="helm/data-quality-monitor/values-${ENVIRONMENT}.yaml"

if [[ ! -f "${VALUES_FILE}" ]]; then
  echo "Values file not found: ${VALUES_FILE}" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/../ci/render_helm_chart.sh" "helm/data-quality-monitor" "${VALUES_FILE}" "${RELEASE_NAME}" "${NAMESPACE}"
