#!/usr/bin/env bash
set -euo pipefail

HELM_IMAGE="${HELM_IMAGE:-alpine/helm:3.16.4}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.59.1}"
TERRAFORM_IMAGE="${TERRAFORM_IMAGE:-hashicorp/terraform:1.9.8}"
ARGOCD_IMAGE="${ARGOCD_IMAGE:-quay.io/argoproj/argocd:v2.13.3}"

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required when using containerized DevOps tool fallbacks." >&2
    exit 1
  fi
}

run_helm() {
  if command -v helm >/dev/null 2>&1; then
    helm "$@"
    return
  fi

  ensure_docker
  docker run --rm \
    -v "$(pwd):/work" \
    -w /work \
    "$HELM_IMAGE" \
    "$@"
}

run_trivy() {
  if command -v trivy >/dev/null 2>&1; then
    trivy "$@"
    return
  fi

  ensure_docker
  mkdir -p .tmp/trivy-cache
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$(pwd):/work" \
    -v "$(pwd)/.tmp/trivy-cache:/root/.cache/trivy" \
    -w /work \
    "$TRIVY_IMAGE" \
    "$@"
}

run_terraform() {
  if command -v terraform >/dev/null 2>&1; then
    terraform "$@"
    return
  fi

  ensure_docker

  local kubeconfig_mount=()
  if [[ -n "${KUBECONFIG:-}" && -f "${KUBECONFIG}" ]]; then
    kubeconfig_mount=(-e KUBECONFIG=/root/.kube/config -v "${KUBECONFIG}:/root/.kube/config:ro")
  elif [[ -f "${HOME}/.kube/config" ]]; then
    kubeconfig_mount=(-e KUBECONFIG=/root/.kube/config -v "${HOME}/.kube/config:/root/.kube/config:ro")
  fi

  docker run --rm \
    -v "$(pwd):/work" \
    -w /work \
    "${kubeconfig_mount[@]}" \
    "$TERRAFORM_IMAGE" \
    "$@"
}

run_argocd() {
  if command -v argocd >/dev/null 2>&1; then
    argocd "$@"
    return
  fi

  ensure_docker
  docker run --rm \
    -e ARGOCD_AUTH_TOKEN="${ARGOCD_AUTH_TOKEN:-}" \
    "$ARGOCD_IMAGE" \
    argocd "$@"
}
