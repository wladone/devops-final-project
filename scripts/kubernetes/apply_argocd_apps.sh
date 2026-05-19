#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENTS="${1:-dev staging prod}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required to apply the Argo CD manifests." >&2
  exit 1
fi

if ! kubectl config current-context >/dev/null 2>&1; then
  echo "No Kubernetes context is configured. Enable Docker Desktop Kubernetes or point kubectl to a cluster first." >&2
  exit 1
fi

kubectl apply -f argocd/project.yaml

read -r -a ENV_ARRAY <<< "$ENVIRONMENTS"
for ENV_NAME in "${ENV_ARRAY[@]}"; do
  APP_FILE="argocd/app-${ENV_NAME}.yaml"
  if [[ ! -f "${APP_FILE}" ]]; then
    echo "Argo CD application manifest not found: ${APP_FILE}" >&2
    exit 1
  fi

  kubectl apply -f "${APP_FILE}"
done
