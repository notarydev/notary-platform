# IAM roles for the ECS tasks.

# Execution role: lets ECS pull images and write logs.
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-ecs-execution"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task role: used by the running API container.
resource "aws_iam_role" "api_task" {
  name = "${local.name_prefix}-api-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-api-task"
  }
}

# Inline policy: read evidence bucket, KMS sign/decrypt, read secrets, S3 Get/Put.
resource "aws_iam_role_policy" "api_task" {
  name = "${local.name_prefix}-api-task-policy"
  role = aws_iam_role.api_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadEvidenceBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.evidence.arn,
          "${aws_s3_bucket.evidence.arn}/*"
        ]
      },
      {
        Sid    = "KmsSignDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Sign",
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GetPublicKey"
        ]
        Resource = aws_kms_key.signing.arn
      },
      {
        Sid    = "ReadSecrets"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.database.arn,
          aws_secretsmanager_secret.sealing_keys.arn,
          aws_secretsmanager_secret.signing.arn
        ]
      }
    ]
  })
}
