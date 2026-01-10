# WAI Harvard 2026 Infrastructure
# Provider configuration and data sources

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Get current AWS account ID for KMS policy
data "aws_caller_identity" "current" {}
