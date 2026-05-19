module "platform_namespaces" {
  source = "../../modules/platform_namespaces"

  namespaces = {
    dq-monitor-dev = {
      labels = {
        environment = "dev"
        owner       = "platform"
      }
      annotations = {}
      hard = {
        "requests.cpu"    = "2"
        "requests.memory" = "4Gi"
        "limits.cpu"      = "4"
        "limits.memory"   = "8Gi"
      }
    }
    monitoring = {
      labels = {
        environment = "dev"
        owner       = "platform"
      }
      annotations = {}
      hard        = {}
    }
    argocd = {
      labels = {
        environment = "dev"
        owner       = "platform"
      }
      annotations = {}
      hard        = {}
    }
  }
}
