# Optional Devtron OSS Extension

Devtron is not required for the green local demo, but it is useful if you want a more platform-engineering style Kubernetes UI on top of the same `kind` cluster.

Use it to inspect Kubernetes workloads, deployments, namespaces, and app health from a product-like dashboard. Keep Jenkins, Argo CD, Prometheus, and Grafana as the main demo path; treat Devtron as an optional extra layer.

## Install

```powershell
powershell -ExecutionPolicy Bypass -File scripts/devtron/install.ps1
```

## Open UI

```powershell
powershell -ExecutionPolicy Bypass -File scripts/devtron/port_forward.ps1
```

Then open the URL printed by the script, normally:

```text
http://localhost:28000
```

## Status

```powershell
powershell -ExecutionPolicy Bypass -File scripts/devtron/status.ps1
```

## Why Optional

Devtron is heavier than the rest of the local demo. It can be a strong add-on for interviews, but it should not block the main CI/CD story:

```text
Jenkins -> Docker image -> Ansible classic deploy -> GitOps update -> Argo CD -> Kubernetes -> Prometheus/Grafana
```
