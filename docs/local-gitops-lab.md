# Local GitOps Lab

This lab completes the Kubernetes side of the project on a real local cluster:

1. install host tools (`kind`, `helm`, `terraform`, `trivy`, `argocd`)
2. create a local `kind` cluster
3. serve a local Git repository over `git://localhost:9418`
4. bridge that repo into the cluster as `git://gitops-repo.argocd.svc.cluster.local:9418`
4. install Argo CD in the cluster
5. sync the local application into Kubernetes

Helpful scripts:

- [install_host_tools.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/install_host_tools.ps1)
- [create_cluster.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/kind/create_cluster.ps1)
- [start.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/gitops/start.ps1)
- [bootstrap_local_repo.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/gitops/bootstrap_local_repo.ps1)
- [install_argocd.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/gitops/install_argocd.ps1)
- [bootstrap_app.ps1](C:/Users/vladp/OneDrive/Desktop/Ansible_Project/scripts/gitops/bootstrap_app.ps1)

Useful local URLs after bootstrap:

- GitOps repo source: `git://localhost:9418/data-quality-monitor.git`
- In-cluster GitOps source: `git://gitops-repo.argocd.svc.cluster.local:9418/data-quality-monitor.git`
- Argo CD UI via port-forward: `http://localhost:28080`
- Dashboard via port-forward: `http://localhost:28501`
