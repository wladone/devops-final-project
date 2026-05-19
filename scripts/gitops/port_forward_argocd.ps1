param ()

$ErrorActionPreference = "Stop"
kubectl port-forward svc/argocd-server -n argocd 28080:80
