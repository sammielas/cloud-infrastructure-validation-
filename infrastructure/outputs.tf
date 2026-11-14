output "environment" {
  description = "Selected deployment environment"
  value       = var.environment
}

output "artifact_bucket_name" {
  description = "Name of the application artifacts bucket."
  value       = aws_s3_bucket.application_artifacts.id
}
