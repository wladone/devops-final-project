output "lab_machine_name" {
  description = "Container name of the lab Linux target — used as the Ansible inventory host"
  value       = docker_container.lab_linux_target.name
}

output "lab_machine_ssh_port" {
  description = "Host port that maps to the lab machine's sshd"
  value       = var.ssh_host_port
}

output "lab_machine_ssh_user" {
  description = "Username Ansible logs in as"
  value       = var.target_user
}

output "registry_endpoint" {
  description = "URL of the local OCI registry"
  value       = "http://localhost:${var.registry_host_port}"
}
