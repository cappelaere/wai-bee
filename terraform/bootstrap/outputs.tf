# Outputs for Bootstrap Infrastructure

output "state_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.tfstate.id
}

output "state_bucket_arn" {
  description = "ARN of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.tfstate.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.tflock.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.tflock.arn
}

output "backend_config" {
  description = "Backend configuration to use in main terraform"
  value       = <<-EOT
    
    # Add this to terraform/backend.tf:
    terraform {
      backend "s3" {
        bucket         = "${aws_s3_bucket.tfstate.id}"
        key            = "wai-harvard-2026/terraform.tfstate"
        region         = "${var.aws_region}"
        dynamodb_table = "${aws_dynamodb_table.tflock.name}"
        encrypt        = true
      }
    }
  EOT
}

