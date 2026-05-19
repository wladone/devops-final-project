module "platform_namespaces" {
  source = "../../modules/platform_namespaces"

  namespaces = {
    dq-monitor-staging = {
      labels = {
        environment = "staging"
        owner       = "platform"
      }
      annotations = {}
      hard = {
        "requests.cpu"    = "4"
        "requests.memory" = "8Gi"
        "limits.cpu"      = "8"
        "limits.memory"   = "16Gi"
      }
    }
    monitoring = {
      labels = {
        environment = "staging"
        owner       = "platform"
      }
      annotations = {}
      hard        = {}
    }
    argocd = {
      labels = {
        environment = "staging"
        owner       = "platform"
      }
      annotations = {}
      hard        = {}
    }
  }
}
