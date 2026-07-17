# Variables for the Notary Platform Terraform configuration (single AWS account).

# Region to deploy into. The Phase 1 dev/test account is provisioned in us-east-2.
variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-2"
}

# Resource Groups application ARN, applied as the awsApplication default tag.
# Replace the account id and region with your own deployment's values.
variable "aws_application_arn" {
  description = "myApplications (Resource Groups) ARN for the awsApplication default tag"
  type        = string
  default     = "arn:aws:resource-groups:us-east-2:447633181871:group/Notary/072xw6nolrnxzw18spteuir5vt"
}

# Whether to create a NAT gateway for private-subnet outbound internet.
# Default is false to save cost (~$33/mo) for demo/dev. When false, the API
# service runs in public subnets with a public IP so it can reach ECR and
# Secrets Manager. Set true for a production-style private-subnet deployment.
variable "enable_nat" {
  description = "Create a NAT gateway (true) or run the API in public subnets (false, cheaper)"
  type        = bool
  default     = false
}

# Project name used as a prefix for resources.
variable "project_name" {
  description = "Project name used as a resource name prefix"
  type        = string
  default     = "notary"
}

# Deployment environment (e.g. dev, staging, prod).
variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

# --- REQUIRED (no default): supply via terraform.tfvars / environment ---
# Master database username.
variable "db_username" {
  description = "RDS PostgreSQL master username"
  type        = string
  # No default — must be provided via terraform.tfvars or -var.
}

# Master database password. SENSITIVE — never commit a value.
variable "db_password" {
  description = "RDS PostgreSQL master password (SENSITIVE)"
  type        = string
  sensitive   = true
  # No default — must be provided via terraform.tfvars or -var.
}

# RDS automated backup retention in days. Free-tier accounts must use 0.
# Set to 7+ once the account is upgraded from free tier.
variable "db_backup_retention_days" {
  description = "RDS automated backup retention in days (0 for free tier)"
  type        = number
  default     = 0
}

# RDS instance class.
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# KMS alias for the signing/custody key.
variable "kms_key_alias" {
  description = "KMS alias for the signing/custody key"
  type        = string
  default     = "notary/signing"
}

# Org sealing key secret material. SENSITIVE. Empty string means the value is
# supplied externally / rotated; the secret still stores the provided value.
variable "sealing_key_secret" {
  description = "Org sealing key secret material (SENSITIVE). Empty string allowed."
  type        = string
  sensitive   = true
  default     = ""
}

# OpenAI test API key. SENSITIVE. Empty means placeholder secret only.
variable "openai_api_key" {
  description = "OpenAI test API key (SENSITIVE). Empty string allowed."
  type        = string
  sensitive   = true
  default     = ""
}

# Anthropic test API key. SENSITIVE. Empty means placeholder secret only.
variable "anthropic_api_key" {
  description = "Anthropic test API key (SENSITIVE). Empty string allowed."
  type        = string
  sensitive   = true
  default     = ""
}

# API container image reference for the ECS task (from ECR).
variable "api_image" {
  description = "API container image reference (ECR repo:tag)"
  type        = string
  default     = "notary-api:latest"
}

# CIDR allowed to reach the API on port 8000.
# NOTE: default is open (0.0.0.0/0) for convenience — RESTRICT this in real
# deployments (e.g. to a bastion / ALB / corporate CIDR).
variable "api_ingress_cidr" {
  description = "CIDR allowed to reach the API on port 8000"
  type        = string
  default     = "0.0.0.0/0"
}

# API DNS name. Used only to construct the dashboard_url output.
# Optional — defaults to empty (output will be a relative/host-relative URL).
variable "api_dns" {
  description = "Public DNS name of the API (for dashboard_url output)"
  type        = string
  default     = ""
}
