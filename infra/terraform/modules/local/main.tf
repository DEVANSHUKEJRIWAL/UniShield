# Local development Terraform module — k3d + local databases
terraform {
  required_version = ">= 1.7"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

variable "cluster_name" {
  description = "k3d cluster name"
  type        = string
  default     = "unishield-local"
}

resource "null_resource" "k3d_cluster" {
  triggers = {
    cluster_name = var.cluster_name
  }

  provisioner "local-exec" {
    command = "k3d cluster create ${var.cluster_name} --config infra/k3d-config.yml || true"
  }
}

output "cluster_name" {
  value = var.cluster_name
}
