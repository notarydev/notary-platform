resource "aws_ecr_repository" "api_server" {
  name                 = "${var.project_name}/api-server"
  image_tag_mutability = "MUTABLE"
}

resource "aws_ecr_repository" "replay_engine" {
  name                 = "${var.project_name}/replay-engine"
  image_tag_mutability = "MUTABLE"
}
