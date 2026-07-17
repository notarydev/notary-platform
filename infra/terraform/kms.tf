# KMS key used for signing / custody operations.

resource "aws_kms_key" "signing" {
  description             = "Notary Platform signing and custody key"
  enable_key_rotation    = true
  deletion_window_in_days = 10

  tags = {
    Name = "${local.name_prefix}-signing"
  }
}

resource "aws_kms_alias" "signing" {
  name          = "alias/${var.kms_key_alias}"
  target_key_id = aws_kms_key.signing.key_id
}
