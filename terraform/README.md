# Terraform Bootstrap

This Terraform scaffold is meant for cluster bootstrap tasks around the application platform:

- namespace creation
- standard labels
- optional namespace-level resource quotas

The module targets an existing Kubernetes cluster by using your local `kubeconfig`.

Typical flow:

1. configure `terraform/environments/<env>/terraform.tfvars`
2. run `terraform init`
3. run `terraform plan`
4. run `terraform apply`
