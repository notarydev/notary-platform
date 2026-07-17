# RDS PostgreSQL instance for the Notary Platform.
# Runs in the private subnets via a subnet group. Password comes from the
# sensitive `db_password` variable — never hardcoded.

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  identifier     = "${local.name_prefix}-db"
  engine         = "postgres"
  engine_version = "16"

  instance_class        = var.db_instance_class
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_name  = "${replace(local.project_name, "-", "_")}_${var.environment}"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name_prefix}-db-final"
  deletion_protection      = false

  backup_retention_period = 7

  tags = {
    Name = "${local.name_prefix}-db"
  }
}
