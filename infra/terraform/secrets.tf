# Secrets Manager secrets for the Notary Platform.
# All secret versions are marked sensitive. No secrets are hardcoded.

# Database connection details (json).
resource "aws_secretsmanager_secret" "database" {
  name                    = "${local.name_prefix}/database"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id

  secret_string = jsonencode({
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = aws_db_instance.main.db_name
    username = var.db_username
    password = var.db_password
  })

  # This value is sensitive; do not surface in plan output.
  lifecycle {
    # password/endpoint may rotate; allow updates
    ignore_changes = []
  }
}

# Org sealing keys (json). Uses the sensitive sealing_key_secret variable.
# An empty value means the secret stores an empty string placeholder — rotate
# via your secrets manager / pipeline rather than committing material.
resource "aws_secretsmanager_secret" "sealing_keys" {
  name                    = "${local.name_prefix}/sealing-keys"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-sealing-keys-secret"
  }
}

resource "aws_secretsmanager_secret_version" "sealing_keys" {
  secret_id = aws_secretsmanager_secret.sealing_keys.id

  secret_string = jsonencode({
    sealing_key = var.sealing_key_secret
  })
}

# Signing key reference / KMS configuration (json).
resource "aws_secretsmanager_secret" "signing" {
  name                    = "${local.name_prefix}/signing"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-signing-secret"
  }
}

resource "aws_secretsmanager_secret_version" "signing" {
  secret_id = aws_secretsmanager_secret.signing.id

  secret_string = jsonencode({
    kms_key_id = aws_kms_key.signing.id
  })
}

# OpenAI test API key placeholder. Empty by default; supply via TF_VAR / pipeline.
resource "aws_secretsmanager_secret" "openai" {
  name                    = "${local.name_prefix}/openai"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-openai-secret"
  }
}

resource "aws_secretsmanager_secret_version" "openai" {
  secret_id = aws_secretsmanager_secret.openai.id

  secret_string = jsonencode({
    api_key = var.openai_api_key
  })
}

# Anthropic test API key placeholder. Empty by default; supply via TF_VAR / pipeline.
resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "${local.name_prefix}/anthropic"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-anthropic-secret"
  }
}

resource "aws_secretsmanager_secret_version" "anthropic" {
  secret_id = aws_secretsmanager_secret.anthropic.id

  secret_string = jsonencode({
    api_key = var.anthropic_api_key
  })
}
