# Variables for the Notary Platform Terraform configuration (single AWS account).

# Region to deploy into.
variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

# Resource Groups application ARN, applied as the awsApplication default tag.
# Replace the account id and region with your own deployment's values.
variable "aws_application_arn" {
  description = "myApplications (Resource Groups) ARN for the awsApplication default tag"
  type        = string
  default     = "arn:aws:resource-groups:us-east-1:447633181871:group/Notary/072xw6nolrnxzw18spteuir5vt"
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
