# Releases

## v1.0 — IT School DevOps final submission

**Target submission**: 31 May 2026 to `training34@itschool.ro` and `office@itschool.ro`.

### What's in this release

A complete local-only DevOps platform built around a real Python data product. Every layer of the delivery chain is implemented and verified end-to-end on one machine.

### Mapping to the IT School criteria

| # | Criterion | Where |
|---|---|---|
| 1 | Terraform creates machines | `terraform/modules/lab_machine/` + `terraform/environments/lab/` provision the Ubuntu lab host + local registry. Swappable for `aws_instance` / `azurerm_linux_virtual_machine` / `digitalocean_droplet` against a real cloud. |
| 2 | Ansible configures machines | `ansible/playbook.yml` installs Docker + Compose, renders the production stack, starts containers. Idempotency verified by `scripts/ci/ansible_idempotency.sh` (Jenkins stage runs the playbook twice, asserts `changed=0`). |
| 3 | Jenkins CI/CD | `Jenkinsfile` (17 parameterized stages) + 3 chained jobs + nightly `jenkins/Jenkinsfile.failure-paths` job for negative-path smoke. |
| 4 | Containerized web app | Streamlit + pandas data-quality validator. `Dockerfile` + `docker-compose.yml` + `helm/data-quality-monitor/` (5 env overlays). |
| 5 | README | `README.md` covers tech stack, quickstart, architecture, criteria map. |

### Headline numbers

- **33** pytest cases covering validators, pipeline, dashboard resilience, CSV edge cases, rules YAML validation
- **4** Jenkins jobs (orchestrator, full CI, delivery, nightly failure-paths)
- **2** enforcing gates: SonarQube quality gate (`qualitygate.wait=true`) + Trivy blocking on HIGH/CRITICAL
- **5** Helm values overlays (`dev`, `staging`, `prod`, `kind-local`, `kind-full`)
- **8** stress-matrix data scenarios + **5** progressive quality-ladder datasets
- **~3-4 min** end-to-end stack bring-up via `dq up`

### Goes beyond the criteria

- GitOps reconciliation via Argo CD on a local kind cluster
- Prometheus + Grafana with a 10-panel ops dashboard
- Kyverno policy-as-code admission control
- Single-command CLI (`dq.ps1` + `dq.cmd`) that auto-bypasses the PowerShell execution policy and emits UTF-8 logs
- Resilience tests covering malformed rules YAML, CSV encoding edge cases, dashboard graceful degradation
- Nightly negative-path Jenkins job verifying each gate fails fast on bad input

### Verified before tagging

- All 33 pytest cases pass locally
- Jenkins full job #42 succeeds with both gates enabled (no suppressions)
- Failure-paths job #2 succeeds (all 4 negative-path stages fail-fast as expected)
- Helm matrix renders against all 5 values files
- Terraform lab environment applies cleanly; the dashboard's platform-health card reaches 6/7 services from inside the K8s pod (the 7th is a recursive self-reference, not a bug)

### Suggested commit + tag commands

```powershell
git add .gitignore .dockerignore .gitattributes README.md RELEASES.md
git add src/ tests/ dashboard/ scripts/ ansible/ helm/ argocd/ terraform/ monitoring/ security/ jenkins/ docs/ config/ data/ lab/
git add Dockerfile docker-compose.yml Jenkinsfile pytest.ini requirements.txt requirements-dev.txt sonar-project.properties
git add dq.ps1 dq.cmd
git commit -m "Initial commit: complete local DevOps platform for IT School final project"

git tag -a v1.0 -m "IT School DevOps final submission"
# git push origin master --tags   # once a GitHub remote is set
```

Don't `git add .` blindly — it would include `.scannerwork/`, `.tmp/`, `.venv/`, `.playwright-cli/`, and `reports/` which are runtime artifacts.

### Optional next steps after v1.0

- Switch the Terraform lab module from the Docker provider to `multipass` or `libvirt` for a real VM (closer to what a strict grader expects, but adds an installation step for the user).
- Cut a public GitHub release from the v1.0 tag and link it in the submission email.
- Record a 30-second screen capture of `dq up` for the README — optional, your call.
