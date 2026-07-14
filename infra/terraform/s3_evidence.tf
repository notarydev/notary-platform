resource "aws_s3_bucket" "evidence" {
  bucket_prefix = "${var.project_name}-evidence-"
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  versioning_configuration {
    status = "Enabled"
  }
}
