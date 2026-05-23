# Data Quality Monitoring — Local DevOps Demo

A complete, end-to-end DevOps platform built around a single, realistic workload: validating tabular customer data against configurable quality rules. The full stack — CI, container build, security scan, deploy, GitOps, monitoring — runs on one machine, end-to-end, with one command.

> **What this demonstrates.** A Python data product flowing through every layer of a modern delivery chain: **Terraform** provisions the lab Linux machine → **Ansible** configures it and installs Docker → **Jenkins** builds the image → **Trivy** scans it → **SonarQube** gates the code → **Argo CD** + **Helm** roll it out to Kubernetes → **Prometheus** + **Grafana** observe it. Designed as a portfolio piece for payments/fintech-style environments where auditability, idempotent deploys, and observable rollouts matter.

---

## For evaluators (received this as an archive)

If you unzipped `data-quality-monitor.zip` from an email and want to see the project end-to-end:

**Prerequisites on your machine**

| Required | Why | Recommended |
|---|---|---|
| Docker Desktop (running) | Hosts the full demo stack (Jenkins, SonarQube, kind, registry, dashboard, Argo CD) | 4.x |
| PowerShell | The `.\dq` entrypoint script | 5.1 on Windows / `pwsh` 7+ on macOS / Linux |
| Python 3.12+ | Only needed for the "tests-only, no Docker" path | 3.12.x |
| ~16 GB RAM, ~20 GB free disk | Ten containers + two kind nodes during the full demo | — |
| Free ports: 8080, 9000, 3000, 9090, 18501, 28080, 28501, 5001 | Service endpoints | — |

**Three ways to evaluate**

```powershell
# 1) Just run the pytest suite — no Docker, ~3 minutes
.\scripts\check_prereqs.ps1
.\scripts\setup_venv.ps1
.\scripts\run_tests.ps1          # 152 tests should pass

# 2) Run the SQL-backed end-to-end pipeline — no Docker, ~30 seconds
$env:PYTHONPATH = "$PWD/src"
python scripts/data/run_sql_pipeline.py --reset
sqlite3 data/db/dq.db "SELECT * FROM analytics_psq_match_summary;"

# 3) Bring up the full demo platform — needs Docker Desktop running, ~4 minutes
.\dq up
```

After option (3), open these URLs (default login `admin / admin123!`):

| Service | URL | What to look at |
|---|---|---|
| Streamlit dashboard (classic) | http://localhost:18501 | Overview tab for the score, **RICOS Coverage** tab for the SQL-backed analytics |
| Streamlit dashboard (k8s) | http://localhost:28501 | Same app, deployed via Helm to a kind cluster |
| Jenkins | http://localhost:8080 | The 17-stage `data-quality-monitor-demo-e2e` job |
| Argo CD | https://127.0.0.1:28080 | GitOps reconciliation status |
| Grafana | http://localhost:3000/d/dq-observability-demo/data-quality-monitoring-operations | 10-panel ops dashboard |
| SonarQube | http://localhost:9000 | Code quality gate |
| Prometheus | http://localhost:9090/targets | Metric scrape targets |

**Where the interesting code lives** — `src/data_quality_monitor/` (the engine, including the SQL-backed pipeline introduced in this submission), `dashboard/app.py` (the Streamlit UI with the live RICOS Coverage tab), `Jenkinsfile` (17 parameterized stages), `helm/` + `argocd/` (the GitOps delivery chain), `ansible/playbook.yml` (the classic delivery chain).

When you're done: `.\dq down` tears everything back down.

---

## Quickstart

The whole platform lives behind a single CLI wrapper. From a plain Windows terminal, no execution-policy setup needed:

```cmd
.\dq up
```

That's it. Behind the scenes the wrapper checks Docker, bypasses the PowerShell execution policy, and runs the full demo bring-up. After ~3 minutes ten containers are up and Jenkins has run the orchestrator pipeline once.

If you're in PowerShell directly:

```powershell
.\dq.ps1 up
```

Once you're up, the same wrapper drives everything else:

| Command | What it does |
|---|---|
| `.\dq up [-light]` | Full stack (default) or Jenkins + SonarQube only (`-light`). |
| `.\dq down` | Tear down Terraform lab + kind cluster + Jenkins/SonarQube. |
| `.\dq status` | One-screen rollup: Docker, containers, Jenkins job results, kind nodes, dashboard URLs. |
| `.\dq build [-strict] [-deploy]` | Trigger the Jenkins full job. `-strict` enables the SonarQube quality gate + Trivy HIGH/CRITICAL blocking. `-deploy` runs the Ansible delivery chain. |
| `.\dq test` | Run the 33-case pytest suite locally — no Docker required. |
| `.\dq logs -service NAME` | Tail logs from `jenkins`, `sonarqube`, `argocd`, `grafana`, or `prometheus`. |

Everything below comes up on `localhost`. Default credentials are `admin / admin123!`.

| Service | URL | Purpose |
|---|---|---|
| **Jenkins** | http://localhost:8080 | CI/CD pipelines |
| **SonarQube** | http://localhost:9000 | Code quality gate |
| **Argo CD** | https://127.0.0.1:28080 | GitOps delivery |
| **Grafana** | http://localhost:3000/d/dq-observability-demo/data-quality-monitoring-operations | Operations dashboard (10 panels) |
| **Prometheus** | http://localhost:9090/targets | Metrics scrape targets |
| **Classic dashboard** | http://localhost:18501 | Streamlit UI on the Linux-style deploy |
| **Kubernetes dashboard** | http://127.0.0.1:28501 | Streamlit UI on the Helm/Argo deploy |

Need a lighter footprint? Use `.\dq up -light` — just Jenkins + SonarQube.

### What `.\dq up` actually does, step by step

If you want to know what's happening while the screen scrolls, here's the timeline:

1. **Docker check** (~5s). If the daemon isn't running, the wrapper launches Docker Desktop and waits for it.
2. **Terraform creates the lab machine** (~30s on first run, ~5s after). `terraform apply` against [terraform/environments/lab](terraform/environments/lab) builds the `dq-lab-linux-target` Ubuntu container and the `dq-lab-registry` OCI registry. This is the "machine" Ansible later configures.
3. **kind cluster + Argo CD come up** (~60s). The GitOps stack: a 2-node kind cluster, Argo CD application controllers, an in-cluster Helm release.
4. **Jenkins + SonarQube containers start** (~60s). Pre-bootstrapped with the demo's admin credentials and Jenkins jobs.
5. **Port-forwards open** (~15s). Argo CD on 28080, Grafana on 3000, Prometheus on 9090, Kubernetes app dashboard on 28501.
6. **Jenkins orchestrator runs** (~90s). The `data-quality-monitor-demo-e2e` job runs the full pipeline: tests → image build → Trivy scan → push → GitOps commit → Argo CD sync → Kubernetes deploy → smoke tests.
7. **Done.** Total ~3-4 minutes. Open any URL from the table above; default login is `admin / admin123!` everywhere.

---

## Technology stack at a glance

**Infrastructure** — Terraform (Docker provider for the lab machine; Kubernetes provider for namespace bootstrap)
**Configuration management** — Ansible (role-based playbook with idempotency check)
**CI/CD** — Jenkins (4 jobs: orchestrator, full CI, delivery, nightly failure-paths)
**Quality gates** — SonarQube (enforcing), Trivy (HIGH/CRITICAL blocking)
**Containers** — Docker, docker-compose
**Kubernetes** — kind (local), Helm (chart with 5 env overlays), Argo CD (GitOps)
**Observability** — Prometheus, Grafana (10-panel ops dashboard), Kyverno (policy-as-code)
**App** — Python 3.12, pandas, Streamlit (web dashboard), pytest (33 cases)

---

## How this maps to the IT School DevOps final project criteria

| # | Criterion | Where it lives in this repo |
|---|---|---|
| 1 | **Terraform creates machines** | [terraform/modules/lab_machine/](terraform/modules/lab_machine) — Docker provider creates the `dq-lab-linux-target` Ubuntu host. [terraform/environments/lab/](terraform/environments/lab) wires it up. Same module structure swaps cleanly for `aws_instance` / `azurerm_linux_virtual_machine` / `digitalocean_droplet` against a real cloud. |
| 2 | **Ansible configures machines** | [ansible/playbook.yml](ansible/playbook.yml) installs Docker Engine + Compose, renders the production docker-compose, starts the dashboard. Idempotency is verified automatically by the [Ansible Idempotency Check](Jenkinsfile) stage (runs playbook twice, asserts `changed=0`). |
| 3 | **CI/CD with Jenkins** | [Jenkinsfile](Jenkinsfile) — 17 parameterized stages, plus a nightly [Jenkinsfile.failure-paths](jenkins/Jenkinsfile.failure-paths) job that verifies each gate fails fast on bad input. SonarQube quality gate is **enforcing** (`qualitygate.wait=true`) and Trivy blocks on HIGH/CRITICAL CVEs. |
| 4 | **Containerized web app** | Streamlit + pandas validator. Single [Dockerfile](Dockerfile). Runs via [docker-compose.yml](docker-compose.yml) on the Linux host **and** via [helm/data-quality-monitor/](helm/data-quality-monitor) on Kubernetes. K8s is bonus per the criteria; both chains share the same image. |
| 5 | **README** | This file. Covers what the app does, every technology used, and how to run it. |
| 6 | **Submission to training34@itschool.ro + office@itschool.ro** | Tag `v1.0` on the public repo; send the repo URL + a short summary by 31 May 2026. |

---

## Architecture

Two parallel delivery chains share the same artifact, so the same image is proven on a classic Linux host **and** on Kubernetes:

```mermaid
flowchart LR
    Dev[Developer] -->|push| Git[(Git)]

    TF[Terraform<br/>lab machine + registry] --> Linux[Linux host<br/>dq-lab-linux-target]

    Git --> Jenkins[Jenkins CI]

    Jenkins --> Tests[Unit + Data Quality]
    Jenkins --> Sonar[SonarQube gate]
    Jenkins --> Build[Docker build]
    Build --> Trivy[Trivy gate]
    Trivy --> Registry[(Registry)]

    Registry -->|classic| Ansible[Ansible<br/>configure host + deploy]
    Ansible --> Linux
    Linux --> SmokeA[Smoke test :18501]

    Registry -->|gitops| GitOps[Git values update]
    GitOps --> Argo[Argo CD]
    Argo --> K8s[Kubernetes<br/>Helm chart]
    K8s --> SmokeB[Smoke test :28501]

    Linux --> Prom[Prometheus]
    K8s --> Prom
    Prom --> Grafana[Grafana]
```

Full write-up: [docs/architecture.md](docs/architecture.md) · Chain comparison: [docs/backend-delivery-chains.md](docs/backend-delivery-chains.md)

---

## Why each tool is here

Designed so every tool in the diagram earns its place:

| Tool | Why it's in the stack |
|---|---|
| **Python + pandas** | The actual product. Validates tabular data against YAML-declared rules; outputs CSV/XLSX/JSON. |
| **Streamlit** | Stakeholder-facing view of latest results, quality ladder, and platform links. |
| **Docker** | One artifact, one runtime, identical from dev laptop to Kubernetes. |
| **Jenkins** | Declarative pipeline with parameterized stages; orchestrates the entire delivery chain. |
| **SonarQube** | Static analysis gate — quality evidence visible in the demo. |
| **Trivy** | Image vulnerability scan before push (advisory in the local demo). |
| **Ansible** | Idempotent Linux deploy — configures the host Terraform created and runs the app under docker-compose. Idempotency verified by a dedicated Jenkins stage. |
| **Helm** | Packaged Kubernetes deploy with environment overlays (`dev`, `staging`, `prod`, plus `kind-local`, `kind-full`). |
| **Argo CD** | GitOps reconciliation — desired state in Git, cluster state follows. |
| **Terraform** | Provisions the lab Linux machine + local OCI registry via the Docker provider. Also bootstraps K8s namespaces with resource quotas. Module structure swaps to AWS / Azure / DigitalOcean providers without changing the rest of the pipeline. |
| **Prometheus + Grafana** | Runtime evidence: pod health, job success/failure, restart trends, data-quality outcomes. |
| **Kyverno** *(optional)* | Policy-as-code guardrails for Kubernetes admission. |

---

## The data story

The default workload is a PSQ customer-base v8 stress dataset. The dataset's lineage lives in [notebooks/PSQ_customer_base_v8_ricos_analysis.ipynb](notebooks/PSQ_customer_base_v8_ricos_analysis.ipynb) — that notebook is the **exploratory source** (RICOS analysis) that framed the schema and stress shapes; the **runtime engine** is the Python package in [src/data_quality_monitor/](src/data_quality_monitor), which is what Jenkins, Ansible, and Helm actually execute. The dashboard's *Notebook viewer* tab renders the `.ipynb` directly so the lineage stays visible alongside the live pipeline results. Two demo modes go beyond a single validation run:

**Stress matrix** — same rules, eight scenarios: clean baseline, missing critical fields, duplicate business keys, invalid domains, invalid dates, null-threshold breaches, large volume, mixed extremes.

**Quality improvement ladder** — five progressive fixes of the same dirty input, each rendered as a step on a score chart in the dashboard:

1. dirty PSQ stress input
2. missing required fields fixed
3. invalid domain values normalized
4. invalid dates and null-threshold breaches repaired
5. duplicate business keys deduplicated

Run it locally:

```powershell
$env:PYTHONPATH = "$PWD/src"
python scripts/data/generate_psq_quality_ladder.py --input data/raw/psq_customer_base_v8_stress.csv --rules config/rules.yml
```

Jenkins runs the same as the `Quality Improvement Ladder` stage in the full demo job.

**RICOS analysis** — pandas port of cells 12-19 of the notebook. Reads the PSQ customer base CSV, generates a deterministic synthetic RICOS reference dataset, applies the same join-key transform the notebook uses (`P_M` + zero-padded merchant id), and writes four derived files to `data/processed/ricos/`:

- `psq_with_ricos_flag.csv` — customer base + `in_ricos_flag` (Y/N) — mirrors the notebook's `projects.riskdatascience.psq_aml_with_ricosflag` table.
- `psq_with_ricos_rich.csv` — customer base + 25 RICOS enrichment columns (identity, risk, screening, UBO/SI counts).
- `psq_match_summary.csv` — match rates by source. Hits **WAY4 ~71% / PASS ~36%**, within ~1pp of the notebook's documented contract.
- `ricos_lookup.csv` — the synthetic source data, for transparency.

```powershell
$env:PYTHONPATH = "$PWD/src"
python scripts/data/run_ricos_analysis.py --input data/raw/psq_customer_base_v8.csv --output-dir data/processed/ricos
```

This is the layer that does what the notebook does — real input data flows through real Python code in [src/data_quality_monitor/ricos_analysis.py](src/data_quality_monitor/ricos_analysis.py) and produces real derived data. Locked in by [tests/test_ricos_analysis.py](tests/test_ricos_analysis.py) (deterministic seed, match-rate tolerance, join-key formula parity with the PySpark original).

**SQL-backed pipeline (end-to-end)** — same engine, but reading from and writing to SQL tables instead of CSVs. Seven tables in a single SQLite database at `data/db/dq.db`:

| Layer | Tables | What they hold |
|---|---|---|
| Source (engine reads) | `psq_customer_base` | 10,000 merchant rows from the customer base CSV. |
| Source (engine reads) | `ricos_merchant_lookup`, `ricos_risk_results`, `ricos_ubo_links` | The three RICOS tables — split exactly like the notebook's `gwgkunde4400` / `presult4400` / `tbbo4400`. |
| Output (engine writes) | `analytics_psq_with_ricos_flag` | Customer base + `in_ricos_flag` (Y/N). One row per merchant. |
| Output (engine writes) | `analytics_psq_with_ricos_rich` | Customer base + all 25 RICOS enrichment columns. Mirrors notebook cell 19. |
| Output (engine writes) | `analytics_psq_match_summary` | Per-source match-rate breakdown — what cell 15 prints. |

```powershell
$env:PYTHONPATH = "$PWD/src"
python scripts/data/run_sql_pipeline.py --reset
```

The orchestrator creates schema, loads sources from the CSV + synthetic RICOS generator, runs the engine, then prints a sample SELECT from the output tables. Inspect any table directly:

```powershell
sqlite3 data/db/dq.db ".tables"
sqlite3 data/db/dq.db "SELECT * FROM analytics_psq_match_summary;"
```

For a real database, set `DQ_DATABASE_URL=postgresql+psycopg2://user:pass@host/db` and the same code path runs against Postgres unchanged. The schema is defined in [src/data_quality_monitor/db_schema.py](src/data_quality_monitor/db_schema.py); the engine is in [src/data_quality_monitor/sql_pipeline.py](src/data_quality_monitor/sql_pipeline.py); tests covering the round-trip are in [tests/test_sql_pipeline.py](tests/test_sql_pipeline.py).

Three follow-ups close the loop:

- **Validator reads from SQL.** The standard quality validator can source its input from any pipeline table instead of a CSV: `python src/main.py --from-sql analytics_psq_with_ricos_flag --rules config/rules.yml --output-dir reports/sql-sourced`. Same rules, same reports, but proving quality on the freshly-engineered data rather than a static file. See [src/data_quality_monitor/data_loader.py](src/data_quality_monitor/data_loader.py)::`load_from_sql_table`.
- **Jenkins runs the SQL pipeline on every CI build.** The `SQL Pipeline` stage in the [Jenkinsfile](Jenkinsfile) (between Quality Improvement Ladder and Helm validation) executes [scripts/ci/run_sql_pipeline.sh](scripts/ci/run_sql_pipeline.sh) and archives the SQLite file + a `match_summary.csv` so you can inspect the engine output from the Jenkins build page.
- **Dashboard surfaces RICOS coverage live.** The Streamlit dashboard has a `RICOS Coverage` tab that queries the analytics tables directly: match-rate KPIs, risk distribution, watchlist hits, and a filterable drill-down. See `render_ricos_panel` in [dashboard/app.py](dashboard/app.py).

---

## Validation rules

YAML-driven, declared in `config/rules.yml`. The starter set checks:

- required columns exist
- critical columns are not null
- business keys are unique
- numeric columns are positive
- date columns are parseable
- allowed values are respected
- null-rate thresholds stay within limits

Each run writes `quality_report.csv`, `quality_report.xlsx`, and `summary.json` to `reports/latest/`.

---

## Local development (no demo platform)

If you just want to iterate on the Python validator without bringing up Jenkins/K8s:

```powershell
.\scripts\check_prereqs.ps1     # verify Python, Docker, etc.
.\scripts\setup_venv.ps1        # create .venv and install deps
.\scripts\run_tests.ps1         # pytest
.\scripts\run_pipeline.ps1      # run validation on PSQ data
.\scripts\run_dashboard.ps1     # serve Streamlit on :8501
```

Or in containers:

```powershell
.\scripts\run_docker.ps1
```

**Recommended Windows setup:** VS Code + WSL2 + Docker Desktop. Open the folder in VS Code and accept the recommended extensions from `.vscode/extensions.json`.

---

## Jenkins pipeline

The [Jenkinsfile](Jenkinsfile) is parameterized so every stage can be toggled. The full chain:

1. Checkout
2. Python env setup
3. Unit tests
4. SonarQube analysis *(optional)*
5. Data quality run
6. Stress matrix
7. Quality improvement ladder
8. Helm chart validation *(optional)*
9. Docker image build
10. Trivy scan *(optional)*
11. Image push *(optional)*
12. Ansible deploy *(optional)*
13. GitOps values update *(optional)*
14. Argo CD sync *(optional)*
15. Kubernetes data-quality job refresh
16. Smoke tests — classic and Kubernetes dashboards

The local Jenkins image under [jenkins/](jenkins) bundles **Ansible, Helm, Trivy, Terraform, Argo CD CLI, and Sonar Scanner**, so the whole pipeline runs without a separate agent.

`.\scripts\demo_full.ps1` creates three jobs and chains them:

- `data-quality-monitor-demo-e2e` — orchestrator; publishes demo links and summary
- `data-quality-monitor-full` — full CI (tests → image → scan → publish)
- `data-quality-monitor-delivery` — Ansible deploy + GitOps update + Argo sync + smoke

Common parameters: `RUN_UNIT_TESTS`, `INPUT_FILE`, `RULES_FILE`, `OUTPUT_DIR`, `RUN_SONAR_SCAN`, `RUN_HELM_VALIDATION`, `RUN_DOCKER_BUILD`, `RUN_SECURITY_SCAN`, `RUN_DOCKER_PUBLISH`, `RUN_DEPLOY`, `RUN_GITOPS_UPDATE`, `RUN_ARGOCD_SYNC`, `REGISTRY_IMAGE`, `IMAGE_TAG_OVERRIDE`. Full list: [Jenkinsfile](Jenkinsfile).

To run a job locally without committing to Git:

```powershell
.\scripts\jenkins\create_job.ps1
.\scripts\jenkins\build_job.ps1
```

After the full demo is up, populate Prometheus/Grafana with extra runner data:

```powershell
.\scripts\demo_populate_observability.ps1 -Runs 5
```

---

## Classic delivery chain (Jenkins → Ansible → Linux)

The Ansible playbook targets Ubuntu/Debian hosts and:

- installs Docker Engine + Compose plugin
- prepares the application directory
- copies rules and sample data
- renders the production Compose file
- starts the dashboard and runner containers

Key files: [ansible/ansible.cfg](ansible/ansible.cfg) · [ansible/inventory.ini](ansible/inventory.ini) · [ansible/group_vars/all.yml](ansible/group_vars/all.yml) · [ansible/playbook.yml](ansible/playbook.yml)

Validate the playbook from Windows (runs inside the local Jenkins container where Ansible is preinstalled):

```powershell
.\scripts\ansible\validate.ps1
```

Real Linux deploy walkthrough: [docs/ansible-linux-deploy.md](docs/ansible-linux-deploy.md)

---

## GitOps delivery chain (Jenkins → Argo CD → Kubernetes)

- [helm/data-quality-monitor/](helm/data-quality-monitor) — Helm chart with `values-dev.yaml`, `values-staging.yaml`, `values-prod.yaml`, plus `values-kind-local.yaml` / `values-kind-full.yaml` for local kind clusters
- [argocd/](argocd) — Argo CD `Application` definitions per environment
- [terraform/](terraform) — namespace and bootstrap resources
- [lab/](lab) — fully local backend delivery lab

Flow: Jenkins builds and scans → updates the values file in Git → Argo CD reconciles the cluster.

Walkthroughs:
- [docs/local-devops-lab.md](docs/local-devops-lab.md) — local Jenkins + registry + Ansible + smoke
- [docs/local-gitops-lab.md](docs/local-gitops-lab.md) — local GitOps + observability
- [docs/backend-delivery-chains.md](docs/backend-delivery-chains.md) — when to use which chain

---

## Observability and security

| Asset | Path |
|---|---|
| Grafana dashboard | [monitoring/grafana/dashboards/data-quality-overview.json](monitoring/grafana/dashboards/data-quality-overview.json) |
| Prometheus alerts | [monitoring/prometheus/alerts/data-quality-alerts.yaml](monitoring/prometheus/alerts/data-quality-alerts.yaml) |
| Trivy config | [security/trivy.yaml](security/trivy.yaml) |
| Kyverno policies | [security/policies/](security/policies) |
| Runbook | [docs/runbook.md](docs/runbook.md) |
| Rollback procedure | [docs/rollback.md](docs/rollback.md) |
| SRE checklist | [docs/sre-checklist.md](docs/sre-checklist.md) |

---

## Project structure

```text
.
├── src/                    # Python data-quality validator + CLI
├── tests/                  # pytest suite
├── config/rules.yml        # YAML-declared validation rules
├── data/                   # PSQ stress datasets (raw + processed)
├── dashboard/              # Streamlit UI
├── Dockerfile              # one image for runner + dashboard
├── docker-compose.yml      # local two-service stack
├── Jenkinsfile             # parameterized CI/CD pipeline
├── ansible/                # roles + playbook for Linux deploy
├── helm/                   # Kubernetes chart + env values
├── argocd/                 # GitOps Application manifests
├── terraform/              # namespace bootstrap
├── monitoring/             # Prometheus alerts + Grafana dashboard
├── security/               # Trivy + Kyverno
├── jenkins/                # local Jenkins image (bundles Ansible/Helm/Trivy/...)
├── scripts/                # demo + ops scripts (PowerShell + Python)
├── lab/                    # local backend delivery lab
└── docs/                   # architecture, runbook, rollback, interview script
```

---

## Suggested reading order

For a guided tour: [docs/rollout-order.md](docs/rollout-order.md) — Python local → dashboard → Docker → Jenkins → Ansible/Linux → production polish.

For an interviewer walkthrough: [docs/interview-script.md](docs/interview-script.md) — what was built, why each tool, what happens when something breaks.

Optional: [docs/devtron-extension.md](docs/devtron-extension.md) — heavier Kubernetes UI overlay (off the default green path).
