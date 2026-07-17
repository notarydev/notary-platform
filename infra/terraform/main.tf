terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Default tags applied to all taggable resources.
  default_tags {
    tags = {
      awsApplication = var.aws_application_arn
      Project        = local.project_name
      Environment    = local.environment
      ManagedBy      = "terraform"
    }
  }
}

locals {
  project_name = var.project_name
  environment  = var.environment

  # Common name prefix for resources in this account/environment.
  name_prefix = "${var.project_name}-${var.environment}"
}
