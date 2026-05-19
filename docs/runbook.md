# Runbook

Day-2 operations for the Data Quality Monitoring platform. Targeted at someone who knows the architecture (see [architecture.md](architecture.md)) and now needs to bring it up, keep it healthy, or fix it under pressure.

For rollback specifically, see [rollback.md](rollback.md). For pre-deploy gates, see [sre-checklist.md](sre-checklist.md).

---

## Standard CI flow

The Jenkins pipeline is parameterized — toggle each stage on the build form. Default flow:

1. Checkout
2. Python environment setup
3. Unit tests (`pytest`)
4. Data quality run on the PSQ stress dataset
5. Stress matrix (8 scenarios)
6. Quality improvement ladder
7. SonarQube analysis *(optional)*
8. Helm chart validation *(optional)*
9. Docker image build
10. Trivy scan *(optional)*
11. Image push to registry *(optional)*
12. Ansible deploy to Linux host *(optional)*
13. GitOps values update + Argo CD sync *(optional)*
14. Smoke tests against both delivery surfaces

If a stage fails, the build stops there. Artifacts up to the failure are retained on the Jenkins build page.

---

## Bring the local platform up

```powershell
.\scripts\demo_full.ps1
```

Wait until all three Jenkins jobs are created and the orchestrator `data-quality-monitor-demo-e2e` is green. After that, populate observability:

```powershell
.\scripts\demo_populate_observability.ps1 -Runs 5
```

Quick check — all endpoints should respond:

| Service | Health probe |
|---|---|
| Jenkins | `curl http://localhost:8080/login` returns 200 |
| SonarQube | `curl http://localhost:9000/api/system/status` reports `UP` |
| Argo CD | `argocd app list --server localhost:28080` lists 3 apps |
| Grafana | `curl http://localhost:3000/api/health` returns `database: ok` |
| Prometheus | `http://localhost:9090/targets` — all up |
| Classic dashboard | `curl http://localhost:18501/` returns 200 |
| Kubernetes dashboard | `curl http://127.0.0.1:28501/` returns 200 |

If any of these fail, jump to the troubleshooting matrix below.

---

## Bring the local platform down

```powershell
.\scripts\demo_light.ps1 -Down       # tears down Jenkins + Sonar only
.\scripts\demo_full.ps1 -Down        # tears down the full stack
```

Persistent state (Jenkins job history, SonarQube DB, Grafana, Prometheus TSDB) is wiped with the volumes — intentional for a demo.

---

## Kubernetes deploy

Day-to-day deploys go through Argo CD. Manual path when you need it:

1. Update the image tag in `helm/data-quality-monitor/values-<env>.yaml`.
2. Render to verify: `helm template data-quality-monitor helm/data-quality-monitor -f helm/data-quality-monitor/values-<env>.yaml`
3. Commit and push.
4. Argo CD reconciles automatically; force with `argocd app sync data-quality-monitor-<env>`.
5. Verify (see post-deploy checks below).

---

## Post-deploy checks

```bash
kubectl get pods -n dq-monitor-<env>
kubectl get cronjob -n dq-monitor-<env>
kubectl get ingress -n dq-monitor-<env>
kubectl get pvc -n dq-monitor-<env>
```

All pods should be `Running`, CronJob `LAST SCHEDULE` should be recent and `LAST SUCCESS` non-empty, and the PVC should be `Bound`.

Then open the dashboard URL and confirm:
- the latest run timestamp is recent
- the quality ladder chart renders with all 5 steps
- the failed-checks table shows the expected counts for the stress dataset

Finally, check Grafana — every panel on the Operations dashboard should have data, and no critical alerts firing in Prometheus.

---

## Troubleshooting matrix

| Symptom | Where to look | Most likely cause |
|---|---|---|
| Jenkins jobs missing after `demo_full.ps1` | Jenkins container logs: `docker logs jenkins` | Job seed script failed; rerun `.\scripts\jenkins\create_job.ps1` |
| SonarQube quality gate stuck `IN_PROGRESS` | `http://localhost:9000/projects` → project page | Scanner ran but webhook didn't fire; force re-analysis or restart Sonar |
| Argo CD app shows `OutOfSync` | Argo UI → app → Diff | Drift from Git; check who edited the cluster manually, then `argocd app sync` |
| Argo CD app shows `Degraded` | Argo UI → app → Pods | Failed Helm render or missing image; see `kubectl describe pod` |
| Dashboard 502 / connection refused | `kubectl logs deploy/<release>-dashboard` | Streamlit crashed during boot; check Python traceback |
| CronJob `LAST SUCCESS` is empty | `kubectl logs job/<cronjob>-<hash>` | Validator crashed — usually rules.yml shape mismatch or missing input file |
| Grafana panels show "No data" | Grafana → panel → Query inspector | Namespace mismatch (panels currently hardcoded to `dq-monitor-dev` — known issue) |
| Prometheus target `DOWN` | `http://localhost:9090/targets` | Service not exposing `/metrics` or NetworkPolicy blocking |
| Ansible playbook hangs on `pull` | Run with `-vvv` | Registry unreachable from the target host; check DNS + credentials |
| Smoke test fails on `:18501` | Linux host: `docker ps` and `docker logs` on dashboard container | Container started but Streamlit not ready — usually slow cold start; increase smoke-test retries |
| Smoke test fails on `:28501` | `kubectl get ingress -n dq-monitor-<env>` | Ingress not provisioned or port-forward not running |
| "image not found" during Ansible deploy | Run `docker pull <image>` manually on host | Tag mismatch between Jenkins push and Ansible vars |
| PVC stuck `Pending` | `kubectl describe pvc -n dq-monitor-<env>` | StorageClass missing or wrong access mode for cluster |

---

## Incident triage workflow

When something is broken in a way that's not obviously in the matrix:

1. **Confirm the surface.** Which dashboard is broken — classic, Kubernetes, or both? If both, the problem is upstream (image, registry, validator). If one, the problem is in that delivery chain.
2. **Find the most recent change.** Jenkins build history, `argocd app history`, or `git log -- helm/`. The "last change" is the prime suspect.
3. **Check pod / container state.**
   - K8s: `kubectl get pods -n <ns>` → `kubectl describe pod <pod>` → `kubectl logs <pod>`
   - Linux: `docker ps` → `docker logs <container>`
4. **Check the inputs.** Did the rules file change? Did the input dataset change? `git log -- config/ data/`.
5. **Check the outputs.** Does `reports/latest/summary.json` exist and parse? If not, the validator failed; if yes but ratios look wrong, the rules or data drifted.
6. **Check observability.** Grafana Operations dashboard — any panel red? Prometheus alerts — anything firing?
7. **Decide: roll forward or roll back.** If the fix is small and obvious, roll forward. Otherwise, follow [rollback.md](rollback.md).

---

## Common interventions

### Force a fresh validation run (Kubernetes)

```bash
kubectl create job --from=cronjob/<release>-runner manual-$(date +%s) -n dq-monitor-<env>
```

### Force a fresh validation run (Linux)

```bash
ssh <host> "cd /opt/data-quality-monitor && docker compose run --rm runner"
```

### Restart the dashboard

```bash
# Kubernetes
kubectl rollout restart deploy/<release>-dashboard -n dq-monitor-<env>

# Linux
ssh <host> "cd /opt/data-quality-monitor && docker compose restart dashboard"
```

### Resync Argo CD app

```bash
argocd app sync data-quality-monitor-<env>
argocd app wait data-quality-monitor-<env> --health
```

### Drain old reports

The PVC fills up over time. To purge older runs:

```bash
kubectl exec -n dq-monitor-<env> deploy/<release>-dashboard -- \
  find /app/reports -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
```

---

## Escalation

For the local demo, there's no escalation path — it's a portfolio piece. For a production-shaped deployment, the escalation matrix would look like:

| Severity | Trigger | Action |
|---|---|---|
| SEV-1 | Both dashboards down >15 min, alerts firing | Page on-call; start incident channel; consider rollback |
| SEV-2 | One delivery surface broken, other healthy | Open ticket; investigate during business hours unless degrading |
| SEV-3 | Validator producing unexpected results | Open ticket; route to data-quality owner |
| SEV-4 | Cosmetic dashboard issue | Backlog |

---

## Related documents

- [architecture.md](architecture.md) — what the platform looks like
- [rollback.md](rollback.md) — how to undo a bad deploy
- [sre-checklist.md](sre-checklist.md) — what "ready" means
- [backend-delivery-chains.md](backend-delivery-chains.md) — both pipelines in detail
- [ansible-linux-deploy.md](ansible-linux-deploy.md) — Linux deploy specifics
- [local-devops-lab.md](local-devops-lab.md) — local lab walkthrough
- [local-gitops-lab.md](local-gitops-lab.md) — local GitOps walkthrough
