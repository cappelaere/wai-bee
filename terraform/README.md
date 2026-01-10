# WAI Harvard 2026 AWS Infrastructure

Terraform configuration for provisioning AWS resources for the WAI Harvard 2026 scholarship processing system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Infrastructure                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │  KMS Key        │    │  S3 Buckets     │    │  State Infra    │ │
│  │  (PII encrypt)  │    │                 │    │                 │ │
│  │                 │    │  - data (PII)   │    │  - tfstate      │ │
│  │  wai-harvard-   │───▶│  - output       │    │  - tflock       │ │
│  │  2026-pii-key   │    │  - logs         │    │  (DynamoDB)     │ │
│  └─────────────────┘    │  - config       │    └─────────────────┘ │
│                         └─────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Resources Created

### Bootstrap (`bootstrap/`)

| Resource | Name | Purpose |
|----------|------|---------|
| S3 Bucket | `wai-harvard-2026-tfstate` | Terraform state storage |
| DynamoDB Table | `wai-harvard-2026-tflock` | State locking |

### Main Infrastructure

| Resource | Name | Description |
|----------|------|-------------|
| KMS Key | `wai-harvard-2026-pii-key` | Customer-managed key for PII encryption |
| S3 Bucket | `wai-harvard-2026-data` | PII data storage (SSE-KMS, 90-day lifecycle) |
| S3 Bucket | `wai-harvard-2026-output` | Non-PII output data (SSE-S3, 180-day lifecycle) |
| S3 Bucket | `wai-harvard-2026-logs` | Application logs (SSE-S3, 180-day lifecycle) |
| S3 Bucket | `wai-harvard-2026-config` | Configuration storage (SSE-S3, 180-day lifecycle) |

### Bucket Details

| Bucket | Encryption | Retention | Versioning | Public Access |
|--------|------------|-----------|------------|---------------|
| `wai-harvard-2026-data` | SSE-KMS (custom key) | 90 days | Enabled | Blocked |
| `wai-harvard-2026-output` | SSE-S3 (AES256) | 180 days | Enabled | Blocked |
| `wai-harvard-2026-logs` | SSE-S3 (AES256) | 180 days | Enabled | Blocked |
| `wai-harvard-2026-config` | SSE-S3 (AES256) | 180 days | Enabled | Blocked |

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- AWS account with permissions to create S3, KMS, and DynamoDB resources

## Deployment

### Step 1: Bootstrap State Infrastructure

First, create the S3 bucket and DynamoDB table for Terraform state management:

```bash
cd terraform/bootstrap
terraform init
terraform plan
terraform apply
```

This creates:
- S3 bucket for state storage (versioned, encrypted)
- DynamoDB table for state locking

### Step 2: Deploy Main Infrastructure

After bootstrap completes, deploy the main resources:

```bash
cd ..  # Back to terraform/
terraform init    # Configures S3 backend
terraform plan
terraform apply
```

## Configuration

### Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region for all resources |
| `environment` | `production` | Environment tag |
| `project` | `wai-harvard-2026` | Project name for tagging |
| `pii_bucket_name` | `wai-harvard-2026-data` | PII data bucket name |
| `output_bucket_name` | `wai-harvard-2026-output` | Output data bucket name |
| `logs_bucket_name` | `wai-harvard-2026-logs` | Logs bucket name |
| `config_bucket_name` | `wai-harvard-2026-config` | Config bucket name |
| `pii_retention_days` | `90` | Days before PII data expires |
| `output_retention_days` | `180` | Days before output data expires |
| `logs_retention_days` | `180` | Days before logs expire |
| `config_retention_days` | `180` | Days before config data expires |

### Customizing Variables

Create a `terraform.tfvars` file:

```hcl
aws_region          = "us-west-2"
environment         = "staging"
pii_retention_days  = 60
```

Or pass via command line:

```bash
terraform apply -var="aws_region=us-west-2" -var="environment=staging"
```

## File Structure

```
terraform/
├── README.md           # This file
├── bootstrap/          # State infrastructure (run first)
│   ├── main.tf         # S3 bucket + DynamoDB table
│   ├── outputs.tf      # State resource outputs
│   ├── variables.tf    # Bootstrap variables
│   └── versions.tf     # Provider versions
├── backend.tf          # Remote state configuration
├── main.tf             # Provider + data sources
├── kms.tf              # KMS key for PII encryption
├── buckets.tf          # S3 bucket definitions
├── variables.tf        # Input variables
├── outputs.tf          # Output values
└── versions.tf         # Terraform/provider versions
```

## Outputs

After applying, the following outputs are available:

```bash
terraform output
```

| Output | Description |
|--------|-------------|
| `pii_bucket_id` | PII data bucket ID |
| `pii_bucket_arn` | PII data bucket ARN |
| `output_bucket_id` | Output data bucket ID |
| `output_bucket_arn` | Output data bucket ARN |
| `logs_bucket_id` | Logs bucket ID |
| `logs_bucket_arn` | Logs bucket ARN |
| `config_bucket_id` | Config bucket ID |
| `config_bucket_arn` | Config bucket ARN |
| `kms_key_id` | KMS key ID |
| `kms_key_arn` | KMS key ARN |
| `kms_key_alias` | KMS key alias |

## Security Features

- **Encryption at Rest**: All buckets use server-side encryption
  - PII bucket: SSE-KMS with customer-managed key (automatic rotation)
  - Other buckets: SSE-S3 (AES-256)
- **Public Access Blocked**: All buckets block public access
- **Versioning**: All buckets have versioning enabled
- **State Locking**: DynamoDB prevents concurrent state modifications
- **State Encryption**: Terraform state is encrypted in S3

## Cleanup

To destroy resources (in reverse order):

```bash
# Destroy main infrastructure
cd terraform
terraform destroy

# Destroy bootstrap (state infrastructure)
# WARNING: This will delete your state file!
cd bootstrap
# Remove prevent_destroy lifecycle rule first, then:
terraform destroy
```

## Troubleshooting

### "Error: S3 bucket already exists"

S3 bucket names are globally unique. If the bucket exists in another account:

```bash
terraform apply -var="pii_bucket_name=my-unique-bucket-name"
```

### "Error acquiring state lock"

Another Terraform process may be running. Check the lock:

```bash
aws dynamodb scan --table-name wai-harvard-2026-tflock
```

Force unlock (use with caution):

```bash
terraform force-unlock LOCK_ID
```

---

**Last Updated**: 2026-01-09  
**Maintained By**: WAI Harvard Infrastructure Team

