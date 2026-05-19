#!/usr/bin/env bash
set -euo pipefail

DASHBOARD_URL="${1:?Dashboard URL is required}"
PORT_FORWARD_PID=""

cleanup() {
  if [[ -n "${PORT_FORWARD_PID}" ]] && kill -0 "${PORT_FORWARD_PID}" >/dev/null 2>&1; then
    kill "${PORT_FORWARD_PID}" >/dev/null 2>&1 || true
    wait "${PORT_FORWARD_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ -n "${K8S_SMOKE_RESOURCE:-}" ]]; then
  : "${K8S_SMOKE_NAMESPACE:?K8S_SMOKE_NAMESPACE is required when K8S_SMOKE_RESOURCE is set}"
  : "${K8S_SMOKE_LOCAL_PORT:?K8S_SMOKE_LOCAL_PORT is required when K8S_SMOKE_RESOURCE is set}"
  : "${K8S_SMOKE_REMOTE_PORT:?K8S_SMOKE_REMOTE_PORT is required when K8S_SMOKE_RESOURCE is set}"

  kubectl -n "${K8S_SMOKE_NAMESPACE}" port-forward "${K8S_SMOKE_RESOURCE}" "${K8S_SMOKE_LOCAL_PORT}:${K8S_SMOKE_REMOTE_PORT}" >/tmp/k8s-smoke-port-forward.log 2>&1 &
  PORT_FORWARD_PID="$!"

  for _ in {1..20}; do
    if curl -fsS "${DASHBOARD_URL}" >/dev/null 2>&1; then
      echo "Smoke test passed for $DASHBOARD_URL"
      exit 0
    fi
    sleep 2
  done

  echo "Smoke test failed for $DASHBOARD_URL" >&2
  cat /tmp/k8s-smoke-port-forward.log >&2 || true
  exit 1
fi

curl -fsS "$DASHBOARD_URL" >/dev/null
echo "Smoke test passed for $DASHBOARD_URL"
