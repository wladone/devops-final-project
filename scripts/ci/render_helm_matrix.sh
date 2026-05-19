#!/usr/bin/env bash
# Render the Helm chart against every environment values file in one pass.
# Surfaces values-file drift (e.g. a key removed from values.yaml that a
# prod overlay still references) before it reaches Argo CD.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHART_PATH="${1:-helm/data-quality-monitor}"
RELEASE_NAME="${2:-data-quality-monitor}"
NAMESPACE="${3:-dq-monitor-dev}"

# Values files to render. Add new env overlays here.
VALUES_FILES=(
  "${CHART_PATH}/values-dev.yaml"
  "${CHART_PATH}/values-staging.yaml"
  "${CHART_PATH}/values-prod.yaml"
  "${CHART_PATH}/values-kind-local.yaml"
  "${CHART_PATH}/values-kind-full.yaml"
)

exit_code=0
for values_file in "${VALUES_FILES[@]}"; do
  if [[ ! -f "$values_file" ]]; then
    echo "Skipping missing values file: $values_file"
    continue
  fi

  echo "===> Rendering ${values_file}"
  if ! "${SCRIPT_DIR}/render_helm_chart.sh" "$CHART_PATH" "$values_file" "$RELEASE_NAME" "$NAMESPACE"; then
    echo "FAIL: helm render against ${values_file}" >&2
    exit_code=1
  fi
done

exit "$exit_code"
