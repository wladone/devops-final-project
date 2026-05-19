#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/devops_tooling.sh"

CHART_PATH="${1:-helm/data-quality-monitor}"
VALUES_FILE="${2:-helm/data-quality-monitor/values-dev.yaml}"
RELEASE_NAME="${3:-data-quality-monitor}"
NAMESPACE="${4:-dq-monitor-dev}"

run_helm lint "$CHART_PATH" --values "$CHART_PATH/values.yaml" --values "$VALUES_FILE"
run_helm template "$RELEASE_NAME" "$CHART_PATH" \
  --namespace "$NAMESPACE" \
  --values "$CHART_PATH/values.yaml" \
  --values "$VALUES_FILE" \
  >/dev/null
