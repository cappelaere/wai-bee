# Variables for Terraform State Infrastructure

variable "aws_region" {
  description = "AWS region for state infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name for resource tagging"
  type        = string
  default     = "wai-harvard-2026"
}

variable "state_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  type        = string
  default     = "wai-harvard-2026-tfstate"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  type        = string
  default     = "wai-harvard-2026-tflock"
}

