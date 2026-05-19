variable "lab_context_path" {
  description = "Absolute path to the lab/ansible-target Dockerfile context"
  type        = string
  default     = "../../../lab/ansible-target"
}

variable "ssh_host_port" {
  description = "Host port mapped to the lab machine's sshd"
  type        = number
  default     = 2222
}

variable "registry_host_port" {
  description = "Host port mapped to the local OCI registry"
  type        = number
  default     = 5001
}
