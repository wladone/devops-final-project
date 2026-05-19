# Rollout Order

Use this order for building, validating, and presenting the project:

1. **Python local**
   - Validate rules, tests, and report outputs.
   - Commands:
     - `.\scripts\run_tests.ps1`
     - `.\scripts\run_pipeline.ps1`

2. **Dashboard local**
   - Open the latest generated report in Streamlit.
   - Command:
     - `.\scripts\run_dashboard.ps1`

3. **Docker**
   - Build and run the same flow in containers.
   - Commands:
     - `docker compose up --build -d`
     - `docker compose ps`
     - `docker compose logs --tail=50`

4. **Jenkins**
   - Use a Linux agent with Python 3, Docker, and optional Ansible installed.
   - The pipeline in `Jenkinsfile` runs tests, the quality job, Docker build, optional push, optional deploy, and smoke test.

5. **Ansible + Linux**
   - Update `ansible/inventory.ini` with the real host.
   - Update `ansible/group_vars/all.yml` with the real image, port, and application directory.
   - Run:
     - `ansible-playbook -i ansible/inventory.ini ansible/playbook.yml --extra-vars "docker_image=<your-image>"`

6. **Production polish**
   - Add real data rules.
   - Add registry credentials in Jenkins.
   - Add monitoring/alerts and a short demo script.

## Current status

- Python local: complete and validated
- Dashboard local: complete and validated
- Docker: complete and validated
- Jenkins: scaffolded and ready for a Linux Jenkins agent
- Ansible: scaffolded and ready for a real Linux host

