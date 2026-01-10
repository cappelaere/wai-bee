# WAI Harvard 2026 S3 Buckets
# Four buckets: PII data (SSE-KMS), output data (SSE-S3), logs (SSE-S3), config (SSE-S3)

# -----------------------------------------------------------------------------
# PII Data Bucket (SSE-KMS, 90 days retention)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "pii_data" {
  bucket = var.pii_bucket_name

  tags = {
    Name        = var.pii_bucket_name
    Purpose     = "PII data storage"
    DataClass   = "sensitive"
    Encryption  = "SSE-KMS"
    RetentionDays = var.pii_retention_days
  }
}

resource "aws_s3_bucket_versioning" "pii_data" {
  bucket = aws_s3_bucket.pii_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pii_data" {
  bucket = aws_s3_bucket.pii_data.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.pii_bucket_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "pii_data" {
  bucket = aws_s3_bucket.pii_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "pii_data" {
  bucket = aws_s3_bucket.pii_data.id

  rule {
    id     = "expire-pii-data"
    status = "Enabled"

    expiration {
      days = var.pii_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# -----------------------------------------------------------------------------
# Output Data Bucket (SSE-S3, 180 days retention)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "output_data" {
  bucket = var.output_bucket_name

  tags = {
    Name        = var.output_bucket_name
    Purpose     = "Output non-PII data storage"
    DataClass   = "internal"
    Encryption  = "SSE-S3"
    RetentionDays = var.output_retention_days
  }
}

resource "aws_s3_bucket_versioning" "output_data" {
  bucket = aws_s3_bucket.output_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "output_data" {
  bucket = aws_s3_bucket.output_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "output_data" {
  bucket = aws_s3_bucket.output_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "output_data" {
  bucket = aws_s3_bucket.output_data.id

  rule {
    id     = "expire-output-data"
    status = "Enabled"

    expiration {
      days = var.output_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# -----------------------------------------------------------------------------
# Application Logs Bucket (SSE-S3, 180 days retention)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "logs" {
  bucket = var.logs_bucket_name

  tags = {
    Name        = var.logs_bucket_name
    Purpose     = "Application logs storage"
    DataClass   = "internal"
    Encryption  = "SSE-S3"
    RetentionDays = var.logs_retention_days
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-logs"
    status = "Enabled"

    expiration {
      days = var.logs_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# -----------------------------------------------------------------------------
# Configuration Bucket (SSE-S3, 180 days retention)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "config" {
  bucket = var.config_bucket_name

  tags = {
    Name        = var.config_bucket_name
    Purpose     = "Configuration storage"
    DataClass   = "internal"
    Encryption  = "SSE-S3"
    RetentionDays = var.config_retention_days
  }
}

resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket = aws_s3_bucket.config.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "config" {
  bucket = aws_s3_bucket.config.id

  rule {
    id     = "expire-config"
    status = "Enabled"

    expiration {
      days = var.config_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

