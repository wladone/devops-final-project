variable "image_tag" {
  description = "Tag used for the lab Linux target image built from lab/ansible-target/"
  type        = string
  default     = "data-quality-monitor/lab-linux-target:local"
}

variable "context_path" {
  description = "Path to the Dockerfile build context for the lab Linux target (absolute or relative to the Terraform working dir)"
  type        = string
}

variable "container_name" {
  description = "Container name registered with the Docker daemon"
  type        = string
  default     = "dq-lab-linux-target"
}

variable "ssh_host_port" {
  description = "Port on the host that maps to the container's sshd"
  type        = number
  default     = 2222
}

variable "registry_image" {
  description = "Image used for the local OCI registry container"
  type        = string
  default     = "registry:2"
}

variable "registry_container_name" {
  description = "Container name for the local registry"
  type        = string
  default     = "dq-lab-registry"
}

variable "registry_host_port" {
  description = "Port on the host that maps to the registry's HTTP API"
  type        = number
  default     = 5001
}

variable "target_user" {
  description = "Username Ansible logs in as on the lab machine"
  type        = string
  default     = "devops"
}

variable "target_password" {
  description = "Password for the lab user — local-only demo credential"
  type        = string
  default     = "devops123!"
  sensitive   = true
}
