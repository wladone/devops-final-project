variable "kubeconfig_path" {
  description = "Path to the kubeconfig file used for cluster authentication."
  type        = string
  default     = "~/.kube/config"
}
