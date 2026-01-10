# Variables for WAI Harvard 2026 S3 Buckets

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
  default     = "production"
}

variable "project" {
  description = "Project name for resource tagging"
  type        = string
  default     = "wai-harvard-2026"
}

variable "pii_bucket_name" {
  description = "Name of the PII data bucket"
  type        = string
  default     = "wai-harvard-2026-data"
}

variable "output_bucket_name" {
  description = "Name of the output (non-PII) data bucket"
  type        = string
  default     = "wai-harvard-2026-output"
}

variable "logs_bucket_name" {
  description = "Name of the application logs bucket"
  type        = string
  default     = "wai-harvard-2026-logs"
}

variable "config_bucket_name" {
  description = "Name of the configuration bucket"
  type        = string
  default     = "wai-harvard-2026-config"
}

variable "pii_retention_days" {
  description = "Number of days to retain PII data before expiration"
  type        = number
  default     = 90
}

variable "output_retention_days" {
  description = "Number of days to retain output data before expiration"
  type        = number
  default     = 180
}

variable "logs_retention_days" {
  description = "Number of days to retain application logs before expiration"
  type        = number
  default     = 180
}

variable "config_retention_days" {
  description = "Number of days to retain configuration data before expiration"
  type        = number
  default     = 180
}

