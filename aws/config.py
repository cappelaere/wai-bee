"""AWS Configuration for WAI Harvard 2026 Processing.

This module contains configuration settings for S3 buckets
and processing parameters.
"""

import os

# S3 Bucket Configuration
PII_BUCKET = os.getenv("WAI_PII_BUCKET", "wai-harvard-2026-data")
OUTPUT_BUCKET = os.getenv("WAI_OUTPUT_BUCKET", "wai-harvard-2026-output")
LOGS_BUCKET = os.getenv("WAI_LOGS_BUCKET", "wai-harvard-2026-logs")

# S3 Path Prefixes
SCHOLARSHIP_PREFIX = os.getenv("WAI_SCHOLARSHIP_PREFIX", "on-campus-May-2026")

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Processing Configuration
TEMP_DIR = os.getenv("WAI_TEMP_DIR", "/tmp/wai-processing")

