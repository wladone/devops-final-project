resource "kubernetes_namespace_v1" "this" {
  for_each = var.namespaces

  metadata {
    name        = each.key
    labels      = each.value.labels
    annotations = each.value.annotations
  }
}

resource "kubernetes_resource_quota_v1" "this" {
  for_each = {
    for name, cfg in var.namespaces : name => cfg
    if length(cfg.hard) > 0
  }

  metadata {
    name      = "${each.key}-quota"
    namespace = kubernetes_namespace_v1.this[each.key].metadata[0].name
  }

  spec {
    hard = each.value.hard
  }
}
