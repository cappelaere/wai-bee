# AWS Resume Processing

Scripts for processing scholarship resumes in AWS S3 with PII removal.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Processing Flow                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   S3: wai-harvard-2026-data (SSE-KMS encrypted)                        │
│   └── on-campus-May-2026/                                               │
│       └── {WAI-ID}/                                                     │
│           └── {WAI-ID}_1.pdf  ─────┐                                   │
│                                     │                                   │
│                                     ▼                                   │
│                            ┌─────────────────┐                         │
│                            │ process_resume  │                         │
│                            │                 │                         │
│                            │ 1. Download PDF │                         │
│                            │ 2. Parse text   │                         │
│                            │ 3. Remove PII   │                         │
│                            │ 4. Upload txt   │                         │
│                            └────────┬────────┘                         │
│                                     │                                   │
│                                     ▼                                   │
│   S3: wai-harvard-2026-output (SSE-S3 encrypted)                      │
│   └── on-campus-May-2026/                                               │
│       └── {WAI-ID}/                                                     │
│           └── {WAI-ID}_resume.txt                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **AWS Credentials**: Configure AWS CLI or set environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

2. **IAM Permissions**: The executing role needs:
   - `s3:GetObject` on `wai-harvard-2026-data`
   - `s3:PutObject` on `wai-harvard-2026-output`
   - `kms:Decrypt` on the PII bucket's KMS key

3. **Python Dependencies**:
   ```bash
   pip install -r aws/requirements.txt
   ```

## Usage

### Process a Single Resume

```bash
python aws/process_resume.py --wai-id 12345
```

### Process Multiple Resumes

```bash
python aws/process_resume.py --wai-id 12345 67890 11111
```

### Process All Resumes

```bash
python aws/process_resume.py --all
```

### Dry Run (List Files)

```bash
python aws/process_resume.py --all --dry-run
```

### Custom Scholarship Prefix

```bash
python aws/process_resume.py --all --scholarship-prefix on-campus-Fall-2026
```

## Configuration

Configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WAI_PII_BUCKET` | `wai-harvard-2026-data` | Source bucket (encrypted) |
| `WAI_OUTPUT_BUCKET` | `wai-harvard-2026-output` | Destination bucket |
| `WAI_SCHOLARSHIP_PREFIX` | `on-campus-May-2026` | S3 path prefix |
| `AWS_REGION` | `us-east-1` | AWS region |
| `WAI_TEMP_DIR` | `/tmp/wai-processing` | Temp directory for downloads |

## Input/Output Format

### Input (PII Bucket)

```
s3://wai-harvard-2026-data/on-campus-May-2026/{WAI-ID}/{WAI-ID}_1.pdf
```

- Encrypted with SSE-KMS (customer-managed key)
- Contains original resume with PII

### Output (Derived Bucket)

```
s3://wai-harvard-2026-output/on-campus-May-2026/{WAI-ID}/{WAI-ID}_resume.txt
```

- Encrypted with SSE-S3 (AES-256)
- Plain text, PII removed
- Metadata includes:
  - `pii-removed`: `true`
  - `pii-types`: Comma-separated list of removed PII types
  - `source-bucket`: Original bucket
  - `source-key`: Original S3 key

## PII Types Detected

The Presidio-based PII remover detects and redacts:

| Entity Type | Example | Replacement |
|-------------|---------|-------------|
| `EMAIL_ADDRESS` | john@example.com | `<EMAIL_ADDRESS>` |
| `PHONE_NUMBER` | +1 (555) 123-4567 | `<PHONE_NUMBER>` |
| `US_SSN` | 123-45-6789 | `<US_SSN>` |
| `CREDIT_CARD` | 4111-1111-1111-1111 | `<CREDIT_CARD>` |
| `US_DRIVER_LICENSE` | D1234567 | `<US_DRIVER_LICENSE>` |
| `IP_ADDRESS` | 192.168.1.1 | `<IP_ADDRESS>` |

**Preserved** (not redacted):
- `PERSON` (names)
- `LOCATION` (addresses, cities)
- `NRP` (nationalities, religions, political groups)

## Error Handling

- **Missing Resume**: Logged as warning, processing continues
- **Parse Failure**: Logged as error, WAI marked as failed
- **Upload Failure**: Logged as error, WAI marked as failed
- **Exit Code**: Non-zero if any WAI processing failed

## Files

| File | Description |
|------|-------------|
| `config.py` | Configuration settings |
| `process_resume.py` | Main processing script |
| `requirements.txt` | Python dependencies |
| `README.md` | This documentation |

## Integration with Terraform

The S3 buckets are provisioned by Terraform in `terraform/`:

```bash
cd terraform/bootstrap && terraform apply  # State infrastructure
cd .. && terraform apply                    # S3 buckets + KMS
```

See [terraform/README.md](../terraform/README.md) for details.

---

**Last Updated**: 2026-01-09

