output "namespace_names" {
  description = "Managed namespace names."
  value       = keys(kubernetes_namespace_v1.this)
}
