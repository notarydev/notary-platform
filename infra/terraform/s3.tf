# S3 evidence bucket with immutability guarantees.
#
# - Versioning enabled
# - Object Lock enabled with a default COMPLIANCE retention of 365 days
# - Bucket policy DENIES delete operations for all principals, enforcing WORM.

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "evidence" {
  bucket              = "notary-evidence-${data.aws_caller_identity.current.account_id}-${var.environment}"
  object_lock_enabled = true

  tags = {
    Name = "${local.name_prefix}-evidence"
  }
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 365
    }
  }
}

# Deny delete (incl. versioned delete) for all principals to enforce immutability.
resource "aws_s3_bucket_policy" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyDeleteForAll"
        Effect    = "Deny"
        Principal = "*"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion",
          "s3:DeleteObject*"
        ]
        Resource = [
          "${aws_s3_bucket.evidence.arn}/*",
          aws_s3_bucket.evidence.arn
        ]
      }
    ]
  })
}
