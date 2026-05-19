module "lab_machine" {
  source = "../../modules/lab_machine"

  context_path       = var.lab_context_path
  ssh_host_port      = var.ssh_host_port
  registry_host_port = var.registry_host_port
}

output "lab_machine_name" {
  value = module.lab_machine.lab_machine_name
}

output "lab_machine_ssh_endpoint" {
  value = "${module.lab_machine.lab_machine_ssh_user}@localhost:${module.lab_machine.lab_machine_ssh_port}"
}

output "registry_endpoint" {
  value = module.lab_machine.registry_endpoint
}
