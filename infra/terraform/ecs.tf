# ECS cluster and the API server Fargate service for the Notary Platform.
#
# Phase 1 note: replay is performed SYNCHRONOUSLY as part of the API request
# path, so there is NO separate replay-worker deployment or SQS queue required
# yet. The ECR repo for the worker (notary-replay-worker) still exists for
# future use. An optional SQS queue block is included (commented) below.

resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

# Security group for the API service (ingress on 8000).
resource "aws_security_group" "api" {
  name        = "${local.name_prefix}-api-sg"
  description = "Allow inbound API traffic on 8000"
  vpc_id      = aws_vpc.main.id

  dynamic "ingress" {
    for_each = var.api_dns != "" ? [1] : []
    content {
      description     = "API port from ALB"
      from_port       = 8000
      to_port         = 8000
      protocol        = "tcp"
      security_groups = [aws_security_group.alb[0].id]
    }
  }

  dynamic "ingress" {
    for_each = var.api_dns == "" ? [1] : []
    content {
      description = "API port"
      from_port   = 8000
      to_port     = 8000
      protocol    = "tcp"
      cidr_blocks = [var.api_ingress_cidr]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-api-sg"
  }
}

# Security group for the RDS instance (ingress 5432 from the API SG).
resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds-sg"
  description = "Allow Postgres access from the API service"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres from API"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-rds-sg"
  }
}

# Fargate task definition for the API server.
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.api_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
      environment = [
        { name = "NOTARY_ENV", value = var.environment },
        { name = "NOTARY_KMS_KEY_ARN", value = aws_kms_key.signing.arn }
      ]
      secrets = [
        { name = "NOTARY_DB_SECRET_ARN", valueFrom = aws_secretsmanager_secret.database.arn },
        { name = "NOTARY_SEALING_KEY_SECRET_ARN", valueFrom = aws_secretsmanager_secret.sealing_keys.arn },
        { name = "NOTARY_SIGNING_KMS_KEY_ID", valueFrom = aws_secretsmanager_secret.signing.arn }
      ]
    }
  ])

  tags = {
    Name = "${local.name_prefix}-api-task"
  }
}

# Fargate service running the API task.
resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # When NAT is disabled (demo/dev), run in public subnets with a public IP so
  # the task can pull from ECR and read Secrets Manager. When NAT is enabled,
  # run in private subnets with no public IP.
  network_configuration {
    subnets          = var.enable_nat ? aws_subnet.private[*].id : aws_subnet.public[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = var.enable_nat ? false : true
  }

  dynamic "load_balancer" {
    for_each = var.api_dns != "" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.api[0].arn
      container_name   = "api"
      container_port   = 8000
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_execution,
  ]
}

# --- OPTIONAL: SQS queue for async replay (Phase 2+) ---
# Phase 1 uses synchronous replay, so this is unused. Uncomment when a
# replay-worker service is introduced.
#
# resource "aws_sqs_queue" "replay" {
#   name                       = "${local.name_prefix}-replay"
#   visibility_timeout_seconds = 900
#   message_retention_seconds  = 1209600
#
#   tags = {
#     Name = "${local.name_prefix}-replay-queue"
#   }
# }
