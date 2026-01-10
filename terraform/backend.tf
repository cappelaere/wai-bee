# Remote State Configuration with S3 and DynamoDB Locking
#
# IMPORTANT: Before using this backend, you must first provision the
# state infrastructure by running:
#
#   cd terraform/bootstrap
#   terraform init
#   terraform apply
#
# Then return here and run:
#   cd terraform
#   terraform init
#

terraform {
  backend "s3" {
    bucket         = "wai-harvard-2026-tfstate"
    key            = "wai-harvard-2026/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "wai-harvard-2026-tflock"
    encrypt        = true
  }
}

