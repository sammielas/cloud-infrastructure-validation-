resource "aws_s3_bucket" "application_artifacts" {
  bucket = "platform-artifacts-local-${var.environment}"

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "ApplicationArtifacts"
  }
}

resource "aws_s3_bucket_public_access_block" "application_artifacts" {
  bucket = aws_s3_bucket.application_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


resource "aws_s3_bucket_server_side_encryption_configuration" "application_artifacts" {
  bucket = aws_s3_bucket.application_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "application_artifacts" {
  bucket = aws_s3_bucket.application_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}
