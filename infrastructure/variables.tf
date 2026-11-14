variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition = contains(
      ["dev", "test", "staging"],
      var.environment
    )

    error_message = "Environment must be dev, test, or staging."
  }
}


variable "s3_endpoint" {
  description = "Endpoint for the local S3-compatible emulator."
  type        = string
  default     = "http://127.0.0.1:4566"

  validation {
    condition = contains([
      "http://127.0.0.1:4566",
      "http://localhost:4566"
    ], var.s3_endpoint)

    error_message = "S3 endpoint must be the approved local Floci endpoint."
  }
}
