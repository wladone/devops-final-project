param ()

$ErrorActionPreference = "Stop"
$serviceName = kubectl get svc -n monitoring -o jsonpath="{range .items[*]}{.metadata.name}{'\n'}{end}" |
    Where-Object { $_ -match "prometheus$" -or $_ -eq "prometheus-operated" } |
    Select-Object -First 1

if (-not $serviceName) {
    throw "Could not find a Prometheus service in namespace monitoring."
}

kubectl port-forward ("svc/" + $serviceName) -n monitoring 9090:9090
