terraform {
  required_version = ">= 1.6.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  # On Windows Docker Desktop the host defaults to the npipe socket; on
  # Linux/macOS it falls back to the unix socket. Both are detected
  # automatically when host is left blank.
}
