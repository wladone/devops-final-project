module "platform_namespaces" {
  source = "../../modules/platform_namespaces"

  namespaces = {
    dq-monitor-prod = {
      labels = {
        environment = "prod"
        owner       = "platform"
      }
      annotations = {}
      hard = {
        "requests.cpu"    = "8"
        "requests.memory" = "16Gi"
        "limits.cpu"      = "16"
        "limits.memory"   = "32Gi"
      }
    }
    monitoring = {
      labels = {
        environment = "prod"
        owner       = "platform"
      }
      annotations = {}
      hard        = {}
    }
    argocd = {
      labels = {
        environment = "prod"
        owner       = "platform"
      }
      annotations = {}
      hard        = {}
    }
  }
}
