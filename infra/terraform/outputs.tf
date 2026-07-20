# Outputs for the Notary Platform Terraform configuration.

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "ecr_api_url" {
  description = "ECR repository URL for the API image"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_worker_url" {
  description = "ECR repository URL for the replay-worker image"
  value       = aws_ecr_repository.replay_worker.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.address
  sensitive   = false
}

output "evidence_bucket_name" {
  description = "S3 evidence bucket name"
  value       = aws_s3_bucket.evidence.id
}

output "evidence_bucket_arn" {
  description = "S3 evidence bucket ARN"
  value       = aws_s3_bucket.evidence.arn
}

output "kms_key_id" {
  description = "KMS signing key ID"
  value       = aws_kms_key.signing.key_id
}

output "kms_key_arn" {
  description = "KMS signing key ARN"
  value       = aws_kms_key.signing.arn
}

output "secrets_arns" {
  description = "Map of secret names to ARNs"
  value = {
    database     = aws_secretsmanager_secret.database.arn
    sealing_keys = aws_secretsmanager_secret.sealing_keys.arn
    signing      = aws_secretsmanager_secret.signing.arn
    openai       = aws_secretsmanager_secret.openai.arn
    anthropic    = aws_secretsmanager_secret.anthropic.arn
  }
}

output "app_url" {
  description = "Constructed Notary Platform SPA URL"
  value       = var.api_dns == "" ? "http://localhost:8000/app/" : "https://api.${var.api_dns}/app/"
}

output "alb_dns_name" {
  description = "ALB DNS name (for CNAME/alias reference)"
  value       = var.api_dns != "" ? aws_lb.main[0].dns_name : ""
}

output "route53_nameservers" {
  description = "Nameservers for the Route53 zone (must be set at the domain registrar)"
  value       = var.api_dns != "" ? aws_route53_zone.main[0].name_servers : []
}

