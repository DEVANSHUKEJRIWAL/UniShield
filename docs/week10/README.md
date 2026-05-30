# Week 10 — Cloud (Terraform, EKS, CI/CD, Observability)

## Deliverables

- [x] AWS Terraform: VPC, RDS, ElastiCache, WAF, IAM pod identity scaffold
- [x] Helm chart templates (deployment, service, ingress)
- [x] CD deploy workflow with Helm lint + smoke test (`.github/workflows/deploy.yml`)
- [x] Prometheus `/metrics` endpoint + middleware
- [x] Ingress + TLS manifest (`infra/k8s/ingress/unishield.yaml`)

## Notes

Full EKS cluster provisioning requires AWS credentials and `terraform apply` in `infra/terraform/modules/aws/`.

```bash
helm lint infra/helm/unishield -f infra/helm/unishield/values.local.yml
curl http://localhost:8000/metrics
```
