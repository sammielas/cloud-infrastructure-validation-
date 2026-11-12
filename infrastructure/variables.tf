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
