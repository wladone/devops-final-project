# Argo CD

These manifests define a simple GitOps model for the application:

- `project.yaml` creates the shared Argo CD project
- `app-dev.yaml` auto-syncs development
- `app-staging.yaml` auto-syncs staging
- `app-prod.yaml` is intended for controlled production syncs

Before applying them:

1. replace `repoURL` with your real Git repository
2. make sure the `argocd` namespace exists
3. create the target namespaces or let Argo CD create them
