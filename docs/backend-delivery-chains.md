# Backend Delivery Chains

This project now supports two backend-oriented delivery stories.

## Flow 1: Jenkins -> Docker build -> push -> Ansible deploy -> smoke test

### Infrastructure involved

1. `Git repository`
2. `Jenkins server or agent`
3. `Container registry`
4. `Linux target host`
5. `Dashboard endpoint`

For a fully local proof-of-concept, this repository now also includes a lab that provides:

- a local registry on `localhost:5001`
- a Linux SSH target on `localhost:2222`
- helper scripts under [scripts/lab](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/lab)

### What happens

1. Jenkins runs tests and the data quality job.
2. Jenkins builds a versioned image such as `registry.example.com/data-quality-monitor:42`.
3. Jenkins pushes the image to the container registry.
4. Jenkins calls Ansible with `docker_image=<pushed image>`.
5. The Linux host pulls the image and starts the Docker Compose stack.
6. Jenkins hits the dashboard URL and fails the release if the endpoint is down.

### Jenkins parameters

- `REGISTRY_IMAGE`
- `REGISTRY_CREDENTIALS_ID`
- `RUN_DEPLOY=true`
- `INVENTORY_PATH`
- `SSH_CREDENTIALS_ID`
- `DASHBOARD_URL`

### Required credentials

- Registry username and password for the image push
- SSH key for the Linux target host

For the local lab, the inventory uses demo-only credentials stored in [lab/ansible/inventory.ini](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/lab/ansible/inventory.ini), so you can validate the chain before switching to a real VM.

## Flow 2: Jenkins -> image -> Git update -> Argo CD -> Kubernetes

### Infrastructure involved

1. `Git repository`
2. `Jenkins server or agent`
3. `Container registry`
4. `Argo CD server`
5. `Kubernetes cluster`
6. `Dashboard endpoint or ingress`

### What happens

1. Jenkins runs tests and builds the new image.
2. Jenkins pushes the image to the registry.
3. Jenkins updates the target Helm values file with the new image tag.
4. Jenkins commits and pushes the GitOps change to the branch watched by Argo CD.
5. Argo CD pulls the updated Git revision and syncs the cluster.
6. Kubernetes rolls out the dashboard deployment and schedules the runner CronJob.
7. Jenkins can optionally call Argo CD directly and then run a smoke test against the ingress URL.

To make this path reproducible from the repo, use:

- [scripts/kubernetes/render_env_stack.sh](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/kubernetes/render_env_stack.sh) for Helm rendering
- [scripts/kubernetes/apply_argocd_apps.sh](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/kubernetes/apply_argocd_apps.sh) for Argo CD application bootstrap
- [scripts/ci/run_terraform_validate.sh](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/ci/run_terraform_validate.sh) for Terraform validation

### Jenkins parameters

- `REGISTRY_IMAGE`
- `REGISTRY_CREDENTIALS_ID`
- `RUN_GITOPS_UPDATE=true`
- `GITOPS_VALUES_FILE`
- `GITOPS_TARGET_BRANCH`
- `GITOPS_PUSH_REMOTE`
- `GITOPS_PUSH_CREDENTIALS_ID`
- `GIT_USER_NAME`
- `GIT_USER_EMAIL`
- `RUN_ARGOCD_SYNC=true`
- `ARGOCD_APP_NAME`
- `ARGOCD_SERVER`
- `ARGOCD_AUTH_TOKEN_CREDENTIALS_ID`
- `DASHBOARD_URL`

### Required credentials

- Registry credentials for the image push
- SSH key or Git push credentials for the GitOps repository
- Argo CD auth token if Jenkins is allowed to trigger a sync directly

## Why both flows matter

- The `Ansible` flow shows classic infrastructure and server automation.
- The `Argo CD` flow shows modern GitOps delivery to Kubernetes.

Together they make the backend story much stronger for a DevOps role because they prove:

- CI and image management
- artifact promotion
- server automation
- GitOps automation
- Kubernetes rollout ownership
- post-deploy validation
