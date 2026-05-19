# Local DevOps Lab

This repository now contains a runnable local backend lab for the classic delivery path:

1. Jenkins runs tests and the data quality job
2. Jenkins builds the Docker image
3. Jenkins pushes the image into a local registry
4. Jenkins calls Ansible against a local Linux SSH target
5. The target host runs `docker compose up -d`
6. Jenkins executes a smoke test against the deployed dashboard

## Components

- [lab/docker-compose.yml](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/lab/docker-compose.yml)
- [lab/ansible/inventory.ini](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/lab/ansible/inventory.ini)
- [scripts/lab/start.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/lab/start.ps1)
- [scripts/lab/run_ansible_demo.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/lab/run_ansible_demo.ps1)

## What this proves

- registry push works in the delivery chain
- Ansible deploy is no longer a placeholder
- the Linux target model is testable locally
- smoke testing becomes part of the release path

## Expected endpoints

- Jenkins: `http://localhost:8080`
- Registry: `http://localhost:5001`
- Linux target SSH: `localhost:2222`
- Deployed dashboard after Ansible: `http://localhost:18501`
