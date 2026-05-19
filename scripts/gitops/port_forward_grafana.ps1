param ()

$ErrorActionPreference = "Stop"
$serviceName = kubectl get svc -n monitoring -o jsonpath="{range .items[*]}{.metadata.name}{'\n'}{end}" |
    Where-Object { $_ -match "grafana" } |
    Select-Object -First 1

if (-not $serviceName) {
    throw "Could not find a Grafana service in namespace monitoring."
}

kubectl port-forward ("svc/" + $serviceName) -n monitoring 3000:80
