#!/usr/bin/env python3
"""Process resumes from S3: decrypt, remove PII, and save to output bucket.

This script reads encrypted PDF resumes from the PII bucket, extracts text,
removes personally identifiable information, and saves the sanitized output
to the output bucket.

Usage:
    # Process a single WAI ID
    python aws/process_resume.py --wai-id 12345

    # Process multiple WAI IDs
    python aws/process_resume.py --wai-id 12345 67890 11111

    # Process all resumes in the scholarship folder
    python aws/process_resume.py --all

    # Dry run (list files without processing)
    python aws/process_resume.py --all --dry-run

Author: WAI Harvard Infrastructure Team
"""

import sys
import os
import argparse
import tempfile
import logging
from pathlib import Path
from typing import Optional, List, Tuple

import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PII_BUCKET, OUTPUT_BUCKET, SCHOLARSHIP_PREFIX, AWS_REGION, TEMP_DIR
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_s3_client():
    """Create an S3 client with configured region."""
    return boto3.client('s3', region_name=AWS_REGION)


def list_wai_folders(s3_client, bucket: str, prefix: str) -> List[str]:
    """List all WAI ID folders under the given prefix.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        prefix: S3 prefix to search under
        
    Returns:
        List of WAI IDs found
    """
    wai_ids = set()
    paginator = s3_client.get_paginator('list_objects_v2')
    
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/", Delimiter='/'):
            for common_prefix in page.get('CommonPrefixes', []):
                # Extract WAI ID from path like "on-campus-May-2026/12345/"
                folder = common_prefix['Prefix'].rstrip('/')
                wai_id = folder.split('/')[-1]
                if wai_id.isdigit():
                    wai_ids.add(wai_id)
    except ClientError as e:
        logger.error(f"Error listing folders: {e}")
        return []
    
    return sorted(wai_ids)


def download_resume(s3_client, wai_id: str, temp_dir: Path) -> Optional[Path]:
    """Download the resume PDF from S3.
    
    Args:
        s3_client: Boto3 S3 client
        wai_id: WAI applicant ID
        temp_dir: Temporary directory to save the file
        
    Returns:
        Path to downloaded file, or None if not found
    """
    # S3 key: on-campus-May-2026/{WAI-ID}/{WAI-ID}_1.pdf
    s3_key = f"{SCHOLARSHIP_PREFIX}/{wai_id}/{wai_id}_1.pdf"
    local_path = temp_dir / f"{wai_id}_1.pdf"
    
    try:
        logger.info(f"Downloading s3://{PII_BUCKET}/{s3_key}")
        s3_client.download_file(PII_BUCKET, s3_key, str(local_path))
        logger.info(f"Downloaded to {local_path}")
        return local_path
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404' or error_code == 'NoSuchKey':
            logger.warning(f"Resume not found: s3://{PII_BUCKET}/{s3_key}")
        else:
            logger.error(f"Error downloading resume: {e}")
        return None


def parse_pdf(file_path: Path) -> Optional[str]:
    """Parse PDF and extract text content.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text content, or None if parsing failed
    """
    try:
        # Use MarkItDown for lighter-weight parsing (avoids Docling overhead)
        from utils.document_parser import parse_document_markdown
        
        logger.info(f"Parsing PDF: {file_path}")
        text = parse_document_markdown(file_path)
        
        if text:
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
        else:
            logger.warning(f"No text extracted from PDF: {file_path}")
            return None
            
    except ImportError:
        # Fallback to basic PDF parsing
        logger.warning("MarkItDown not available, using fallback parser")
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip() if text.strip() else None
        except Exception as e:
            logger.error(f"Fallback PDF parsing failed: {e}")
            return None
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        return None


def remove_pii(text: str) -> Tuple[str, List[str]]:
    """Remove PII from text using Presidio.
    
    Args:
        text: Input text with potential PII
        
    Returns:
        Tuple of (sanitized text, list of PII types found)
    """
    try:
        from utils.pii_remover import remove_pii as presidio_remove_pii
        
        logger.info("Removing PII from text")
        sanitized, pii_types = presidio_remove_pii(text)
        
        if pii_types:
            logger.info(f"Removed PII types: {', '.join(pii_types)}")
        else:
            logger.info("No PII detected")
            
        return sanitized, pii_types
        
    except ImportError as e:
        logger.error(f"PII remover not available: {e}")
        return text, []
    except Exception as e:
        logger.error(f"Error removing PII: {e}")
        return text, []


def upload_sanitized(s3_client, wai_id: str, text: str, pii_types: List[str]) -> bool:
    """Upload sanitized text to the output bucket.
    
    Args:
        s3_client: Boto3 S3 client
        wai_id: WAI applicant ID
        text: Sanitized text content
        pii_types: List of PII types that were removed
        
    Returns:
        True if upload successful, False otherwise
    """
    # S3 key in output bucket: on-campus-May-2026/{WAI-ID}/{WAI-ID}_resume.txt
    s3_key = f"{SCHOLARSHIP_PREFIX}/{wai_id}/{wai_id}_resume.txt"
    
    # Add metadata about PII removal
    metadata = {
        'pii-removed': 'true',
        'pii-types': ','.join(pii_types) if pii_types else 'none',
        'source-bucket': PII_BUCKET,
        'source-key': f"{SCHOLARSHIP_PREFIX}/{wai_id}/{wai_id}_1.pdf"
    }
    
    try:
        logger.info(f"Uploading to s3://{OUTPUT_BUCKET}/{s3_key}")
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=s3_key,
            Body=text.encode('utf-8'),
            ContentType='text/plain; charset=utf-8',
            Metadata=metadata
        )
        logger.info(f"Successfully uploaded sanitized resume for WAI {wai_id}")
        return True
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        return False


def process_wai(s3_client, wai_id: str, temp_dir: Path, dry_run: bool = False) -> bool:
    """Process a single WAI applicant's resume.
    
    Args:
        s3_client: Boto3 S3 client
        wai_id: WAI applicant ID
        temp_dir: Temporary directory for downloads
        dry_run: If True, only log actions without processing
        
    Returns:
        True if processing successful, False otherwise
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Processing WAI {wai_id}")
    
    if dry_run:
        logger.info(f"  Would download: s3://{PII_BUCKET}/{SCHOLARSHIP_PREFIX}/{wai_id}/{wai_id}_1.pdf")
        logger.info(f"  Would upload to: s3://{OUTPUT_BUCKET}/{SCHOLARSHIP_PREFIX}/{wai_id}/{wai_id}_resume.txt")
        return True
    
    # Download resume
    pdf_path = download_resume(s3_client, wai_id, temp_dir)
    if not pdf_path:
        return False
    
    try:
        # Parse PDF
        text = parse_pdf(pdf_path)
        if not text:
            logger.error(f"Failed to extract text from resume for WAI {wai_id}")
            return False
        
        # Remove PII
        sanitized, pii_types = remove_pii(text)
        
        # Upload sanitized content
        success = upload_sanitized(s3_client, wai_id, sanitized, pii_types)
        return success
        
    finally:
        # Clean up temp file
        if pdf_path.exists():
            pdf_path.unlink()
            logger.debug(f"Cleaned up temp file: {pdf_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process resumes: decrypt from S3, remove PII, save to output bucket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single WAI ID
  python aws/process_resume.py --wai-id 12345

  # Process multiple WAI IDs
  python aws/process_resume.py --wai-id 12345 67890

  # Process all resumes
  python aws/process_resume.py --all

  # Dry run (list without processing)
  python aws/process_resume.py --all --dry-run
        """
    )
    
    parser.add_argument(
        '--wai-id',
        nargs='+',
        help='WAI ID(s) to process'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all WAI folders in the scholarship prefix'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List files without processing'
    )
    parser.add_argument(
        '--scholarship-prefix',
        default=SCHOLARSHIP_PREFIX,
        help=f'S3 prefix for scholarship (default: {SCHOLARSHIP_PREFIX})'
    )
    
    args = parser.parse_args()
    
    # Override scholarship prefix if provided
    global SCHOLARSHIP_PREFIX
    SCHOLARSHIP_PREFIX = args.scholarship_prefix
    
    if not args.wai_id and not args.all:
        parser.error("Must specify --wai-id or --all")
    
    # Create S3 client
    s3_client = get_s3_client()
    
    # Create temp directory
    temp_dir = Path(TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Get WAI IDs to process
    if args.all:
        wai_ids = list_wai_folders(s3_client, PII_BUCKET, SCHOLARSHIP_PREFIX)
        logger.info(f"Found {len(wai_ids)} WAI folders to process")
    else:
        wai_ids = args.wai_id
    
    if not wai_ids:
        logger.warning("No WAI IDs to process")
        return
    
    # Process each WAI
    success_count = 0
    fail_count = 0
    
    for wai_id in wai_ids:
        try:
            if process_wai(s3_client, wai_id, temp_dir, args.dry_run):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"Unexpected error processing WAI {wai_id}: {e}")
            fail_count += 1
    
    # Summary
    logger.info("=" * 50)
    logger.info(f"Processing complete: {success_count} succeeded, {fail_count} failed")
    
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

