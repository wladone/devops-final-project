terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# The lab Linux target is the "machine" the Ansible playbook configures.
# Building it as a Terraform-managed docker_image + docker_container resource
# means Terraform owns the lifecycle of the host that Ansible then provisions,
# matching the classic IaaS → CM split (Terraform creates the box, Ansible
# configures it).
#
# On a real engagement this module would call aws_instance / azurerm_linux_virtual_machine /
# digitalocean_droplet instead — the rest of the pipeline (Ansible, Jenkins,
# Helm) does not care which provider created the host.

resource "docker_image" "lab_linux_target" {
  name = var.image_tag

  build {
    context = var.context_path
    build_args = {
      TARGET_USER     = var.target_user
      TARGET_PASSWORD = var.target_password
    }
  }
}

resource "docker_container" "lab_linux_target" {
  name     = var.container_name
  hostname = var.container_name
  image    = docker_image.lab_linux_target.image_id
  restart  = "unless-stopped"

  ports {
    internal = 22
    external = var.ssh_host_port
  }

  # Mount the host docker socket so the lab machine can talk to the same
  # daemon when Ansible deploys docker-compose stacks onto it.
  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  volumes {
    volume_name    = docker_volume.target_app.name
    container_path = "/opt/data-quality-monitor"
  }
}

resource "docker_volume" "target_app" {
  name = "${var.container_name}-app"
}

resource "docker_image" "registry" {
  name = var.registry_image
}

resource "docker_container" "registry" {
  name    = var.registry_container_name
  image   = docker_image.registry.image_id
  restart = "unless-stopped"

  env = [
    "REGISTRY_STORAGE_DELETE_ENABLED=true",
  ]

  ports {
    internal = 5000
    external = var.registry_host_port
  }

  volumes {
    volume_name    = docker_volume.registry_data.name
    container_path = "/var/lib/registry"
  }
}

resource "docker_volume" "registry_data" {
  name = "${var.registry_container_name}-data"
}
