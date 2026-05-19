#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/devops_tooling.sh"

PROJECT_DIR="${1:-.}"
DOCKER_IMAGE="${2:-}"
TRIVY_CONFIG="${PROJECT_DIR}/security/trivy.yaml"
TRIVY_TIMEOUT="${TRIVY_TIMEOUT:-10m}"
TRIVY_SEVERITY="${TRIVY_SEVERITY:-HIGH,CRITICAL}"
TRIVY_ALLOW_FINDINGS="${TRIVY_ALLOW_FINDINGS:-false}"
TRIVY_ALLOW_FAILURE="${TRIVY_ALLOW_FAILURE:-$TRIVY_ALLOW_FINDINGS}"
COMMON_SKIP_DIRS=(
  --skip-dirs .venv
  --skip-dirs .tmp
  --skip-dirs __pycache__
  --skip-dirs reports/ci
  --skip-dirs reports/latest
)

if [[ -n "$DOCKER_IMAGE" ]]; then
  image_args=(
    --config "$TRIVY_CONFIG"
    --timeout "$TRIVY_TIMEOUT"
    --severity "$TRIVY_SEVERITY"
    --scanners vuln
  )

  # Trivy's default exit code is 0 even when findings are reported. The trivy.yaml
  # config file's "exit-code: 1" is silently ignored by some Trivy versions when
  # other CLI flags are also passed, so we set it explicitly here.
  if [[ "$TRIVY_ALLOW_FINDINGS" == "true" ]]; then
    image_args+=(--exit-code 0)
  else
    image_args+=(--exit-code 1)
  fi

  if ! run_trivy image "${image_args[@]}" "$DOCKER_IMAGE"; then
    if [[ "$TRIVY_ALLOW_FAILURE" == "true" ]]; then
      echo "WARNING: Trivy image scan failed, but TRIVY_ALLOW_FAILURE=true so the local demo will continue." >&2
      exit 0
    fi

    exit 1
  fi

  exit 0
fi

fs_exit_code=1
if [[ "$TRIVY_ALLOW_FINDINGS" == "true" ]]; then
  fs_exit_code=0
fi

if ! run_trivy fs \
    --config "$TRIVY_CONFIG" \
    --timeout "$TRIVY_TIMEOUT" \
    --severity "$TRIVY_SEVERITY" \
    --exit-code "$fs_exit_code" \
    --scanners vuln,misconfig \
    "${COMMON_SKIP_DIRS[@]}" \
    "$PROJECT_DIR"; then
  if [[ "$TRIVY_ALLOW_FAILURE" == "true" ]]; then
    echo "WARNING: Trivy filesystem scan failed, but TRIVY_ALLOW_FAILURE=true so the local demo will continue." >&2
    exit 0
  fi

  exit 1
fi
