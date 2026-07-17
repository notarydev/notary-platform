# CloudWatch log group for ECS task logs.

resource "aws_cloudwatch_log_group" "main" {
  name              = "/aws/ecs/${local.name_prefix}"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-logs"
  }
}
