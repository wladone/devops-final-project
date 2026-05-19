# Interview Walkthrough — 5-Minute Script

A spoken walkthrough of the project for a DevOps / platform / SRE interview. Tuned for payments and fintech audiences (Worldline-style), where the bar is **auditability, idempotent deploys, and observable rollouts**.

The format is a 30-second hook, three ~60-second beats, and a closing on failure modes. Use the headings as cue cards; the prose underneath is what to say roughly, not verbatim.

---

## 0. 30-second pitch

> "This is a Data Quality Monitoring platform. The product itself is a Python validator that checks tabular customer data against YAML-declared rules and writes CSV, XLSX, and JSON reports. I built it so I could practice running a realistic workload through every layer of a modern delivery chain — Jenkins, Docker, registry, Ansible to a Linux host, and Helm to Kubernetes via Argo CD, with Prometheus and Grafana on top. The whole stack comes up locally with one PowerShell command."

**Show:** `.\scripts\demo_full.ps1` running, then the Jenkins dashboard with three green jobs.

---

## 1. The two delivery chains *(~60s)*

> "There are two chains, and they share the same artifact, so the same image is proven on a classic Linux deploy **and** on Kubernetes."

**Chain A — Classic:**
> "Jenkins builds the image, Trivy scans it, the image lands in a local registry. Then an Ansible playbook installs Docker on a Linux target, renders a Compose file, and brings up the dashboard and runner containers. A smoke test hits port 18501 to prove it's alive."

**Chain B — GitOps:**
> "Same image. This time Jenkins updates the `values.yaml` in Git with the new tag. Argo CD watches that file and reconciles the cluster — Helm chart applied, pods rolled. Smoke test on 28501."

> "The point is that the same artifact, same SonarQube gate, same Trivy scan flows through two very different deploy models. If the platform decision changes — say we move from VM-based to Kubernetes — the build half of the pipeline doesn't move."

**Show:** Argo CD UI, Synced/Healthy, then both dashboards loaded side-by-side.

---

## 2. Why each tool is in the stack *(~60s)*

> "I tried to make sure every tool earns its place."

| Tool | The one-sentence justification |
|---|---|
| Python + pandas | The product. Everything else exists to deliver and observe it. |
| Docker | One artifact from laptop to Kubernetes — no "works on my machine." |
| Jenkins | Declarative, parameterized, every stage individually toggleable for fast feedback. |
| SonarQube | Static analysis evidence. Code quality visible in the demo. |
| Trivy | Image vulnerability scan before push — security shifted left. |
| Ansible | Idempotent Linux deploy. Re-runnable, audited, no snowflake servers. |
| Helm | Kubernetes packaging with `dev`/`staging`/`prod` overlays. |
| Argo CD | GitOps. Git is the source of truth for what's running. |
| Prometheus + Grafana | Runtime evidence. Pod health, job outcomes, restart trends, data quality scores. |

> "If a reviewer asked me to remove one tool, I'd be able to defend why each is here — and which two could share responsibilities if we had to simplify."

---

## 3. The product itself — data quality matters *(~60s)*

> "On the data side, the workload is a customer-base dataset extracted from a real PSQ notebook. The validator runs eight stress scenarios — clean baseline, missing critical fields, duplicate business keys, invalid domains, invalid dates, null-threshold breaches, high volume, and mixed extremes."

> "There's also a 'quality improvement ladder' — the same dirty input progressively fixed in five steps, and the dashboard renders the score climbing. That's the part I'd show a business stakeholder. Engineering wants the matrix; the business wants the ladder."

> "Rules are YAML — required columns, uniqueness, null-rate thresholds, allowed values, date parsing, positive numerics. Adding a rule is a config change, not a code change."

**Show:** the Streamlit dashboard with the ladder chart climbing 5 steps.

---

## 4. What happens when it breaks *(~60s)*

This is the question that separates demos from real platforms.

> "Three failure modes I'd talk through:"

**Bad data:**
> "If the input data fails validation, the Jenkins data-quality stage fails — `summary.json` shows the failed checks. The image still builds and deploys behind a feature flag because the pipeline separates 'build the artifact' from 'gate on data outcomes' — but Grafana panels show the regression, and there's a Prometheus alert for it."

**Bad image:**
> "If Trivy finds something critical, the gate flags it. In this local demo Trivy is advisory so the demo stays green — in a real environment I'd switch it to fail-the-build for High and Critical CVEs, with an exception process via a `.trivyignore` reviewed by security."

**Bad deploy:**
> "If the Ansible deploy fails the smoke test on `:18501`, the Jenkins job fails — `docs/rollback.md` describes the manual rollback. If the Kubernetes deploy goes bad, Argo CD shows OutOfSync or Degraded, and you can either revert the Git commit (and Argo reconciles back) or use `argocd app rollback`. The Git-as-source-of-truth model means rollback is *always* a Git operation, which is auditable."

**Show:** `docs/rollback.md` and `docs/runbook.md`.

---

## 5. Closing — what I'd do next *(~30s)*

> "Things I haven't done that I'd prioritize for a real environment:"

- **Strict policy gates** — turn Trivy and SonarQube from advisory to blocking.
- **Secrets** — wire in HashiCorp Vault or sealed-secrets; nothing in plaintext.
- **Multi-environment promotion** — explicit promotion stage from `staging` to `prod` with an approval gate.
- **Network policies** — default-deny in Kubernetes, allowlist explicitly.
- **DR** — backup the PVC, exercise restore.

> "I kept the demo runnable on one laptop on purpose. The point is to show the shape of the platform; the production version would swap localhost endpoints for cloud equivalents but the same architecture."

---

## Likely follow-up questions

**"Why Jenkins and not GitHub Actions or GitLab CI?"**
> Jenkins is what most regulated enterprises still run, and I wanted the demo to reflect that reality. The pipeline logic is portable — most stages are shell-driven and would move to Actions in a day.

**"Why Ansible *and* Helm? Pick one."**
> Different surfaces. Ansible owns OS-level state (Docker installed, directories, users). Helm owns application state inside Kubernetes. In a Kubernetes-only world I'd drop Ansible, but lots of payments shops still run mixed estates.

**"How would you scale this past one box?"**
> The Jenkins agent moves to a real pool, the registry moves to ECR/GHCR/Harbor, Kubernetes becomes EKS/AKS/GKE, and Prometheus becomes a managed Prometheus or Cortex. The Helm chart and Argo CD apps don't change.

**"What's the riskiest part of this stack?"**
> The Git-as-source-of-truth bit cuts both ways. A bad commit to `values-prod.yaml` is a production change. Mitigation: branch protection on `main`, mandatory PR review on `helm/**` and `argocd/**`, signed commits for the deploy bot.

**"What did you learn that surprised you?"**
> How much of the value is in the boring middle — the Compose file rendering, the smoke test, the Grafana panel layout. The flashy tools all converge; the differentiator is whether the rollout is observable and the rollback is one Git revert away.

---

## Cue card — one-line answers

| Question | Answer |
|---|---|
| One command to run? | `.\scripts\demo_full.ps1` |
| Two delivery chains? | Ansible → Linux, and GitOps → Kubernetes |
| Where is the data quality evidence? | Streamlit dashboards, Jenkins artifacts, Grafana panels |
| Where is the security evidence? | SonarQube quality gate, Trivy report in build artifacts |
| Where is the rollback procedure? | `docs/rollback.md` — Git revert for K8s, `ansible-playbook` re-run for Linux |
| Where is the architecture? | `docs/architecture.md` and the diagram in the README |
