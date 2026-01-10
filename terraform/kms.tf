# KMS Key for PII Bucket Encryption

resource "aws_kms_key" "pii_bucket_key" {
  description             = "KMS key for WAI Harvard 2026 PII data bucket encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "pii-bucket-key-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow S3 Service"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name    = "${var.project}-pii-key"
    Purpose = "PII data encryption"
  }
}

resource "aws_kms_alias" "pii_bucket_key_alias" {
  name          = "alias/${var.project}-pii-key"
  target_key_id = aws_kms_key.pii_bucket_key.key_id
}

