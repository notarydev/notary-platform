resource "aws_secretsmanager_secret" "application" {
  name_prefix = "${var.project_name}/application/"
}
