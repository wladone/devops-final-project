# Ansible Linux Deploy

Use this when you are ready to deploy the project to a real Ubuntu or Debian Linux host.

## 1. Update the inventory

Edit [ansible/inventory.ini](ansible/inventory.ini) and replace the sample host with your server details.

Example:

```ini
[data_quality_hosts]
prod-linux ansible_host=203.0.113.10 ansible_user=ubuntu ansible_port=22
```

## 2. Set the Docker image you want to deploy

Edit [ansible/group_vars/all.yml](ansible/group_vars/all.yml).

Minimum change:

```yaml
docker_image: your-registry/data-quality-monitor:latest
```

If you want Jenkins to deploy a build-specific tag, that value will be passed at runtime from the pipeline.

## 3. Validate the playbook locally

If local Jenkins is running, you can validate the Ansible syntax from Windows:

```powershell
.\scripts\ansible\validate.ps1
```

This runs `ansible-playbook --syntax-check` inside the Jenkins container.

## 4. Run the deploy from Linux, WSL, or Jenkins

From a Linux shell, WSL, or a Jenkins agent with Ansible and SSH access:

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml
```

With a specific image tag:

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml \
  --extra-vars "docker_image=your-registry/data-quality-monitor:42"
```

## 5. Verify the target host

After a successful deploy, verify on the Linux host:

```bash
docker compose -f /opt/data-quality-monitor/docker-compose.yml --env-file /opt/data-quality-monitor/.env ps
curl http://127.0.0.1:8501
```

The deployed files will be under `/opt/data-quality-monitor`.

## 6. Enable Jenkins deploys

In Jenkins, the deploy stage becomes active when:

- `RUN_DEPLOY = true`
- `INVENTORY_PATH = ansible/inventory.ini`
- `SSH_CREDENTIALS_ID` points to an SSH key that can reach the Linux host
- `REGISTRY_IMAGE` points to an image the host can pull

The Jenkins pipeline then calls the playbook and passes the built image tag through `docker_image`.
