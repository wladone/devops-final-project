# Local Jenkins

This folder contains a local Jenkins setup for validating the repository pipeline on your machine.

## What is included

- custom Jenkins image with Python, Docker CLI, Git, curl, Ansible, Helm, Trivy, Terraform, Argo CD CLI, and Sonar Scanner
- preinstalled Jenkins plugins needed by the project pipeline
- Configuration as Code (JCasC) for a local admin user
- Docker Compose file for quick startup

## Default login

If you do not override the values in `.env`, the local login is:

- username: `admin`
- password: `admin123!`

Change these values before using the setup beyond a local demo.

The full local demo also provisions the same demo password for SonarQube, Grafana, and Argo CD through:

```powershell
.\scripts\setup_demo_accounts.ps1
```

## Start locally

From the repository root:

```powershell
.\scripts\jenkins\start.ps1
```

Open [http://localhost:8080](http://localhost:8080).

## Stop locally

```powershell
.\scripts\jenkins\stop.ps1
```

## Tail logs

```powershell
.\scripts\jenkins\logs.ps1
```

## Recommended Jenkins job setup

1. Push this repository to GitHub, GitLab, or another Git server.
2. In Jenkins, create a new **Pipeline** job.
3. Choose **Pipeline script from SCM**.
4. Configure the repository URL and credentials if needed.
5. Keep `Jenkinsfile` as the script path.
6. Run the pipeline with defaults first.

## Fully local alternative

If you just want to validate Jenkins locally without pushing to Git yet:

```powershell
.\scripts\jenkins\create_job.ps1
.\scripts\jenkins\build_job.ps1
```

This creates a pipeline job called `data-quality-monitor-local` and runs it against the mounted project at `/workspace/data-quality-monitor`.

## Optional credentials

The pipeline supports these optional Jenkins parameters:

- `REGISTRY_CREDENTIALS_ID`
- `SSH_CREDENTIALS_ID`
- `SONAR_TOKEN_CREDENTIALS_ID`
- `ARGOCD_AUTH_TOKEN_CREDENTIALS_ID`

Use them only when you are ready to push images or deploy with Ansible.
