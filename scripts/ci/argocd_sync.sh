#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/devops_tooling.sh"

ARGOCD_APP_NAME="${1:?Argo CD app name is required}"
ARGOCD_SERVER="${2:-}"
ARGOCD_TIMEOUT="${3:-300}"
ARGOCD_SYNC_MODE="${ARGOCD_SYNC_MODE:-server}"
ARGOCD_NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"

if [[ "${ARGOCD_SYNC_MODE}" == "core" ]]; then
  if ! command -v kubectl >/dev/null 2>&1; then
    echo "kubectl is required for ARGOCD_SYNC_MODE=core." >&2
    exit 1
  fi

  kubectl annotate application "${ARGOCD_APP_NAME}" -n "${ARGOCD_NAMESPACE}" argocd.argoproj.io/refresh=hard --overwrite >/dev/null

  deadline=$((SECONDS + ARGOCD_TIMEOUT))
  while (( SECONDS < deadline )); do
    app_json="$(kubectl get application "${ARGOCD_APP_NAME}" -n "${ARGOCD_NAMESPACE}" -o json)"
    sync_status="$(printf '%s' "${app_json}" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("status",{}).get("sync",{}) or {}).get("status",""))')"
    health_status="$(printf '%s' "${app_json}" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("status",{}).get("health",{}) or {}).get("status",""))')"

    if [[ "${sync_status}" == "Synced" && "${health_status}" == "Healthy" ]]; then
      echo "Argo CD application ${ARGOCD_APP_NAME} is synced and healthy."
      exit 0
    fi

    sleep 5
  done

  kubectl describe application "${ARGOCD_APP_NAME}" -n "${ARGOCD_NAMESPACE}"
  echo "Timed out waiting for ${ARGOCD_APP_NAME} to become Synced and Healthy." >&2
  exit 1
fi

if [[ -z "${ARGOCD_SERVER}" ]]; then
  echo "ARGOCD_SERVER is required when ARGOCD_SYNC_MODE=server." >&2
  exit 1
fi

if [[ -z "${ARGOCD_AUTH_TOKEN:-}" ]]; then
  echo "ARGOCD_AUTH_TOKEN must be set before running this script." >&2
  exit 1
fi

run_argocd app sync "$ARGOCD_APP_NAME" \
  --server "$ARGOCD_SERVER" \
  --auth-token "$ARGOCD_AUTH_TOKEN" \
  --grpc-web

run_argocd app wait "$ARGOCD_APP_NAME" \
  --server "$ARGOCD_SERVER" \
  --auth-token "$ARGOCD_AUTH_TOKEN" \
  --grpc-web \
  --health \
  --timeout "$ARGOCD_TIMEOUT"
