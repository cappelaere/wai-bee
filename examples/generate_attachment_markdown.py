#!/usr/bin/env python3
"""
Generate Markdown versions of attachments using MarkItDown.

This script is an alternate path for document parsing that uses the
`markitdown` library (via utils.document_parser.parse_document_markdown)
to convert original attachment files into Markdown and save them under:

    outputs/<Scholarship>/<WAI>/markdown/<attachment_stem>.md

It does NOT change the existing Docling + PII-removal pipeline; it's
intended for experimentation and inspection of richer Markdown output.

Usage:
    # Generate Markdown for all WAI folders (default 20) in Delaney Wings
    python examples/generate_attachment_markdown.py Delaney_Wings

    # Limit the number of WAI folders processed
    python examples/generate_attachment_markdown.py Delaney_Wings --max-wai 5

    # Only process a single WAI number
    python examples/generate_attachment_markdown.py Delaney_Wings --wai 100439
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

# Ensure project root on path when run from examples/
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.folder_scanner import scan_scholarship_folder, get_wai_number
from utils.attachment_scanner import find_attachment_files
from utils.document_parser import parse_document_markdown
from utils.logging_config import setup_logging, get_logger
from utils.config import config


def generate_markdown_for_scholarship(
    scholarship: str,
    wai_number: Optional[str] = None,
    max_wai: Optional[int] = None,
    max_files_per_wai: int = 5,
) -> None:
    """Generate Markdown for attachments for a given scholarship."""
    logger = get_logger(__name__)

    scholarship_folder = Path("data") / scholarship / "Applications"
    if not scholarship_folder.exists():
        raise FileNotFoundError(f"Scholarship applications folder not found: {scholarship_folder}")

    logger.info(f"Generating Markdown for attachments in: {scholarship_folder}")

    # Determine which WAI folders to process
    wai_folders = []
    if wai_number:
        wai_path = scholarship_folder / wai_number
        if not wai_path.exists():
            raise FileNotFoundError(f"WAI folder not found: {wai_path}")
        wai_folders = [wai_path]
    else:
        wai_folders = scan_scholarship_folder(str(scholarship_folder), max_wai)

    if not wai_folders:
        logger.warning("No WAI folders found to process")
        return

    logger.info(f"Found {len(wai_folders)} WAI folders to process")

    outputs_dir = Path(config.OUTPUTS_DIR)

    for wai_folder in wai_folders:
        wai = get_wai_number(wai_folder)
        logger.info(f"\nProcessing WAI: {wai}")

        attachment_files = find_attachment_files(wai_folder, max_files=max_files_per_wai)
        if not attachment_files:
            logger.info(f"  No attachment files found in {wai}")
            continue

        logger.info(f"  Found {len(attachment_files)} attachment files")

        # Markdown output directory: outputs/<scholarship>/<WAI>/attachments
        # We keep Markdown files alongside the redacted text attachments,
        # using a .md extension for the same stem.
        attachments_dir = outputs_dir / scholarship / wai / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)

        for idx, attachment in enumerate(attachment_files, 1):
            logger.info(f"    [{idx}/{len(attachment_files)}] Converting {attachment.name} -> Markdown")

            md_text = parse_document_markdown(attachment)
            if not md_text:
                logger.warning(f"      Skipping {attachment.name}: no Markdown extracted")
                continue
            
            out_path = attachments_dir / f"{attachment.stem}.md"
            try:
                out_path.write_text(md_text, encoding="utf-8")
                logger.info(f"      Saved Markdown to {out_path}")
            except Exception as e:
                logger.error(f"      Error writing Markdown for {attachment.name}: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Markdown versions of attachments using MarkItDown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "scholarship",
        help="Scholarship folder name (e.g., Delaney_Wings or Evans_Wings)",
    )
    parser.add_argument(
        "--wai",
        help="Specific WAI number to process (e.g., 100439). If omitted, processes multiple WAI folders.",
    )
    parser.add_argument(
        "--max-wai",
        type=int,
        default=20,
        help="Maximum number of WAI folders to process when --wai is not specified (default: 20)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=5,
        help="Maximum number of attachment files per WAI to convert (default: 5)",
    )

    args = parser.parse_args()

    # Setup logging using existing utility
    setup_logging()
    logger = get_logger(__name__)

    try:
        generate_markdown_for_scholarship(
            scholarship=args.scholarship,
            wai_number=args.wai,
            max_wai=args.max_wai,
            max_files_per_wai=args.max_files,
        )
        logger.info("Markdown generation complete.")
        return 0
    except Exception as e:
        logger.error(f"Markdown generation failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


