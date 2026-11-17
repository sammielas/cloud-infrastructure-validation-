resource "aws_s3_bucket" "application_artifacts" {
  resource "aws_s3_bucket" "application_artifacts" {
    #checkov:skip=CKV_AWS_144:Local Floci environment has no cross-region replication requirement; review before AWS deployment.
    #checkov:skip=CKV2_AWS_61:Artifact retention policy is not yet defined; review before AWS deployment.
    #checkov:skip=CKV_AWS_18:Access logging architecture is deferred for local emulator testing.
    #checkov:skip=CKV2_AWS_62:No event notification consumer exists in the current architecture.
    #checkov:skip=CKV_AWS_145:SSE-S3 AES256 is the approved local encryption baseline; KMS is deferred.

    bucket = "platform-artifacts-local-${var.environment}"

    # Keep your existing tags and the rest of the file unchanged.
  }
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
