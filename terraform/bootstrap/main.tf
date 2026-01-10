# Bootstrap Infrastructure for Terraform Remote State
# Run this FIRST before the main terraform configuration

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform-bootstrap"
    }
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket for Terraform State
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name    = var.state_bucket_name
    Purpose = "Terraform state storage"
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# DynamoDB Table for State Locking
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "tflock" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name    = var.dynamodb_table_name
    Purpose = "Terraform state locking"
  }
}

