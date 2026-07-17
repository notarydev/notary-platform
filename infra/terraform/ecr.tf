# Elastic Container Registry repositories for the Notary Platform images.

resource "aws_ecr_repository" "api" {
  name                 = "${local.project_name}-api"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${local.name_prefix}-api"
  }
}

resource "aws_ecr_repository" "replay_worker" {
  name                 = "${local.project_name}-replay-worker"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${local.name_prefix}-replay-worker"
  }
}
