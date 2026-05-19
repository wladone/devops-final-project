# Rollback

## Docker / Jenkins

If a bad image was published, redeploy the previous immutable image tag instead of rebuilding `latest`.

## Helm

Use:

```bash
helm history <release> -n <namespace>
helm rollback <release> <revision> -n <namespace>
```

## Argo CD

Use the previous healthy Git revision and sync again:

```bash
argocd app history <app-name>
argocd app rollback <app-name> <id>
```

## Validation After Rollback

1. verify the dashboard is reachable
2. confirm cronjob schedule and last successful run
3. confirm no active alerts remain
