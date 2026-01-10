# Outputs for WAI Harvard 2026 S3 Buckets

# -----------------------------------------------------------------------------
# PII Data Bucket Outputs
# -----------------------------------------------------------------------------

output "pii_bucket_id" {
  description = "The ID of the PII data bucket"
  value       = aws_s3_bucket.pii_data.id
}

output "pii_bucket_arn" {
  description = "The ARN of the PII data bucket"
  value       = aws_s3_bucket.pii_data.arn
}

output "pii_bucket_domain_name" {
  description = "The domain name of the PII data bucket"
  value       = aws_s3_bucket.pii_data.bucket_domain_name
}

# -----------------------------------------------------------------------------
# Output Data Bucket Outputs
# -----------------------------------------------------------------------------

output "output_bucket_id" {
  description = "The ID of the output data bucket"
  value       = aws_s3_bucket.output_data.id
}

output "output_bucket_arn" {
  description = "The ARN of the output data bucket"
  value       = aws_s3_bucket.output_data.arn
}

output "output_bucket_domain_name" {
  description = "The domain name of the output data bucket"
  value       = aws_s3_bucket.output_data.bucket_domain_name
}

# -----------------------------------------------------------------------------
# Logs Bucket Outputs
# -----------------------------------------------------------------------------

output "logs_bucket_id" {
  description = "The ID of the logs bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "The ARN of the logs bucket"
  value       = aws_s3_bucket.logs.arn
}

output "logs_bucket_domain_name" {
  description = "The domain name of the logs bucket"
  value       = aws_s3_bucket.logs.bucket_domain_name
}

# -----------------------------------------------------------------------------
# Config Bucket Outputs
# -----------------------------------------------------------------------------

output "config_bucket_id" {
  description = "The ID of the config bucket"
  value       = aws_s3_bucket.config.id
}

output "config_bucket_arn" {
  description = "The ARN of the config bucket"
  value       = aws_s3_bucket.config.arn
}

output "config_bucket_domain_name" {
  description = "The domain name of the config bucket"
  value       = aws_s3_bucket.config.bucket_domain_name
}

# -----------------------------------------------------------------------------
# KMS Key Outputs
# -----------------------------------------------------------------------------

output "kms_key_id" {
  description = "The ID of the KMS key for PII bucket encryption"
  value       = aws_kms_key.pii_bucket_key.key_id
}

output "kms_key_arn" {
  description = "The ARN of the KMS key for PII bucket encryption"
  value       = aws_kms_key.pii_bucket_key.arn
}

output "kms_key_alias" {
  description = "The alias of the KMS key"
  value       = aws_kms_alias.pii_bucket_key_alias.name
}

