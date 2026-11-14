run "public_access_is_blocked" {
  command = plan

  variables {
    environment = "dev"
  }

  assert {
    condition = alltrue([
      aws_s3_bucket_public_access_block.application_artifacts.block_public_acls,
      aws_s3_bucket_public_access_block.application_artifacts.block_public_policy,
      aws_s3_bucket_public_access_block.application_artifacts.ignore_public_acls,
      aws_s3_bucket_public_access_block.application_artifacts.restrict_public_buckets
    ])

    error_message = "All S3 public access block settings must be enabled."
  }
}


run "default_encryption_is_enabled" {
  command = plan

  variables {
    environment = "dev"
  }

  assert {
    condition = (
      one(
        one(aws_s3_bucket_server_side_encryption_configuration.application_artifacts.rule)
        .apply_server_side_encryption_by_default
      ).sse_algorithm == "AES256"
    )

    error_message = "S3 bucket must use AES256 default encryption."
  }
}

run "bucket_versioning_is_enabled" {
  command = plan

  variables {
    environment = "dev"
  }

  assert {
    condition = (
      one(aws_s3_bucket_versioning.application_artifacts.versioning_configuration).status
      == "Enabled"
    )

    error_message = "S3 bucket versioning must be enabled."
  }
}
