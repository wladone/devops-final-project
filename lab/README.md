# Local DevOps Lab

This lab turns the repository into a self-contained backend demo for:

`Jenkins -> Docker build -> push -> Ansible deploy -> smoke test`

The lab starts two local services:

- a Docker registry on `http://localhost:5001`
- a Linux SSH target on `localhost:2222`

The target host is a lightweight Ubuntu container with:

- `sshd`
- `python3`
- `docker` CLI and Compose plugin
- access to the local Docker socket

Use it together with the Jenkins container to prove the server-oriented delivery chain without renting a cloud VM first.

## Demo credentials

For the lab target only:

- SSH user: `devops`
- SSH password: `devops123!`

These are intentionally local-only demo credentials. Do not reuse them outside the lab.

## Quick start

```powershell
.\scripts\lab\start.ps1
.\scripts\jenkins\start.ps1
.\scripts\jenkins\create_job.ps1
.\scripts\lab\run_ansible_demo.ps1
```

If the run succeeds, Jenkins will deploy the dashboard and the smoke test will hit:

- `http://host.docker.internal:18501` from inside Jenkins
- `http://localhost:18501` from your browser
