param ()

$ErrorActionPreference = "Stop"
$serviceName = kubectl get svc -n dq-monitor-dev -o jsonpath="{range .items[*]}{.metadata.name}{'\n'}{end}" |
    Where-Object { $_ -match "dashboard" } |
    Select-Object -First 1

if (-not $serviceName) {
    throw "Could not find a dashboard service in namespace dq-monitor-dev."
}

kubectl port-forward ("svc/" + $serviceName) -n dq-monitor-dev 28501:8501
