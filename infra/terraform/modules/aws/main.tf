# AWS EKS module — scaffolded for Phase 3 (Week 10)
terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

# Scaffold — provision in Week 10
output "environment" {
  value = var.environment
}

output "region" {
  value = var.region
}
