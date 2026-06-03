variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Target deployment region on Amazon Web Services"
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Execution environment parameter tag"
}

variable "db_password" {
  type        = string
  default     = "DriftGuardSecurePassword55!"
  sensitive   = true
  description = "PostgreSQL administrator security password"
}
