"""Pre-flight validation for scholarship application files.

This module provides functions to scan applicant directories before processing
to detect common issues early:
- Missing primary application files
- Empty files (0 bytes)
- Corrupted PDFs (invalid headers)

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2026-01-02
Version: 1.0.0
License: MIT
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# PDF magic bytes (header signature)
PDF_MAGIC = b'%PDF-'
PDF_MAGIC_LEN = 5


@dataclass
class PreflightIssue:
    """A single validation issue found during preflight check."""
    wai_number: str
    file_name: str
    issue_type: str  # 'missing', 'empty', 'corrupted', 'unreadable'
    message: str
    severity: str = "error"  # 'error' or 'warning'
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.wai_number}/{self.file_name}: {self.message}"


@dataclass
class PreflightResult:
    """Result of preflight validation for all applicants."""
    total_applicants: int = 0
    valid_applicants: int = 0
    invalid_applicants: int = 0
    total_files_checked: int = 0
    issues: List[PreflightIssue] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors (not just warnings) were found."""
        return any(i.severity == "error" for i in self.issues)
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == "warning")
    
    def get_issues_for_wai(self, wai_number: str) -> List[PreflightIssue]:
        """Get all issues for a specific WAI number."""
        return [i for i in self.issues if i.wai_number == wai_number]
    
    def get_invalid_wai_numbers(self) -> List[str]:
        """Get list of WAI numbers with errors."""
        return list(set(i.wai_number for i in self.issues if i.severity == "error"))
    
    def summary(self) -> str:
        """Generate a summary string."""
        lines = [
            "=" * 60,
            "PREFLIGHT CHECK RESULTS",
            "=" * 60,
            f"Total applicants scanned: {self.total_applicants}",
            f"Valid applicants: {self.valid_applicants}",
            f"Invalid applicants: {self.invalid_applicants}",
            f"Total files checked: {self.total_files_checked}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
        ]
        
        if self.issues:
            lines.append("")
            lines.append("Issues found:")
            for issue in self.issues:
                lines.append(f"  {issue}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def check_pdf_headers(file_path: Path) -> Optional[str]:
    """Check if a PDF file has valid headers.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        None if valid, error message string if corrupted.
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(PDF_MAGIC_LEN)
            
            if len(header) < PDF_MAGIC_LEN:
                return f"File too small ({len(header)} bytes), missing PDF header"
            
            if not header.startswith(PDF_MAGIC):
                # Show what we found instead
                try:
                    header_str = header.decode('ascii', errors='replace')[:20]
                except:
                    header_str = str(header[:20])
                return f"Invalid PDF header (found: {header_str!r}, expected: %PDF-)"
            
            # Check for EOF marker (basic integrity)
            f.seek(-128, 2)  # Last 128 bytes
            tail = f.read()
            if b'%%EOF' not in tail:
                return "Missing PDF EOF marker (file may be truncated)"
            
    except PermissionError:
        return "Permission denied - cannot read file"
    except Exception as e:
        return f"Error reading file: {str(e)}"
    
    return None  # Valid


def scan_applicant_files(
    wai_folder: Path,
    wai_number: str,
    required_attachments: int = 5
) -> List[PreflightIssue]:
    """Scan a single applicant folder for file issues.
    
    Args:
        wai_folder: Path to the applicant folder.
        wai_number: WAI number for reporting.
        required_attachments: Minimum number of attachment files expected.
        
    Returns:
        List of PreflightIssue objects for any problems found.
    """
    issues = []
    
    # Find primary application file (pattern: {wai}_{n}.pdf where n is 1-2 digits)
    primary_pattern = re.compile(rf'^{re.escape(wai_number)}_\d{{1,2}}\.pdf$', re.IGNORECASE)
    primary_files = [f for f in wai_folder.iterdir() if primary_pattern.match(f.name)]
    
    if not primary_files:
        issues.append(PreflightIssue(
            wai_number=wai_number,
            file_name="(primary application)",
            issue_type="missing",
            message=f"No primary application file found matching {wai_number}_*.pdf",
            severity="error"
        ))
    else:
        # Check the primary file
        primary_file = primary_files[0]
        
        # Check file size
        try:
            size = primary_file.stat().st_size
            if size == 0:
                issues.append(PreflightIssue(
                    wai_number=wai_number,
                    file_name=primary_file.name,
                    issue_type="empty",
                    message="Primary application file is empty (0 bytes)",
                    severity="error"
                ))
            else:
                # Check PDF headers
                error = check_pdf_headers(primary_file)
                if error:
                    issues.append(PreflightIssue(
                        wai_number=wai_number,
                        file_name=primary_file.name,
                        issue_type="corrupted",
                        message=error,
                        severity="error"
                    ))
        except Exception as e:
            issues.append(PreflightIssue(
                wai_number=wai_number,
                file_name=primary_file.name,
                issue_type="unreadable",
                message=f"Cannot read file: {str(e)}",
                severity="error"
            ))
    
    # Find attachment files (pattern: {wai}_{n}_{m}.pdf)
    attachment_pattern = re.compile(rf'^{re.escape(wai_number)}_\d+_\d+\.pdf$', re.IGNORECASE)
    attachment_files = sorted([f for f in wai_folder.iterdir() if attachment_pattern.match(f.name)])
    
    # Check each attachment file
    valid_attachments = 0
    for att_file in attachment_files:
        try:
            size = att_file.stat().st_size
            if size == 0:
                issues.append(PreflightIssue(
                    wai_number=wai_number,
                    file_name=att_file.name,
                    issue_type="empty",
                    message="Attachment file is empty (0 bytes)",
                    severity="error"
                ))
            else:
                # Check PDF headers
                error = check_pdf_headers(att_file)
                if error:
                    issues.append(PreflightIssue(
                        wai_number=wai_number,
                        file_name=att_file.name,
                        issue_type="corrupted",
                        message=error,
                        severity="error"
                    ))
                else:
                    valid_attachments += 1
        except Exception as e:
            issues.append(PreflightIssue(
                wai_number=wai_number,
                file_name=att_file.name,
                issue_type="unreadable",
                message=f"Cannot read file: {str(e)}",
                severity="error"
            ))
    
    # Check if we have enough valid attachments
    if valid_attachments < required_attachments:
        issues.append(PreflightIssue(
            wai_number=wai_number,
            file_name="(attachments)",
            issue_type="missing",
            message=f"Only {valid_attachments} valid attachments found, expected {required_attachments}",
            severity="warning" if valid_attachments > 0 else "error"
        ))
    
    return issues


def run_preflight_check(
    scholarship_folder: Path,
    wai_numbers: Optional[List[str]] = None,
    max_applicants: Optional[int] = None,
    required_attachments: int = 5,
    stop_on_first_error: bool = False
) -> PreflightResult:
    """Run preflight validation on all applicant files.
    
    Args:
        scholarship_folder: Path to the scholarship folder.
        wai_numbers: Optional list of specific WAI numbers to check.
            If None, scans all applicants in Applications folder.
        max_applicants: Optional maximum number of applicants to check.
        required_attachments: Minimum number of attachment files expected.
        stop_on_first_error: If True, stop scanning after first error.
        
    Returns:
        PreflightResult with validation results.
    """
    result = PreflightResult()
    
    applications_folder = scholarship_folder / "Applications"
    if not applications_folder.exists():
        logger.error(f"Applications folder not found: {applications_folder}")
        result.issues.append(PreflightIssue(
            wai_number="(system)",
            file_name="Applications/",
            issue_type="missing",
            message=f"Applications folder not found: {applications_folder}",
            severity="error"
        ))
        return result
    
    # Get list of WAI numbers to check
    if wai_numbers is None:
        wai_numbers = [
            d.name for d in applications_folder.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        
        # Sort numerically
        def sort_key(name: str):
            try:
                return (0, int(name))
            except ValueError:
                return (1, name)
        
        wai_numbers = sorted(wai_numbers, key=sort_key)
    
    if max_applicants:
        wai_numbers = wai_numbers[:max_applicants]
    
    result.total_applicants = len(wai_numbers)
    
    logger.info(f"Running preflight check on {len(wai_numbers)} applicants...")
    
    for wai_number in wai_numbers:
        wai_folder = applications_folder / wai_number
        
        if not wai_folder.exists():
            result.issues.append(PreflightIssue(
                wai_number=wai_number,
                file_name="(folder)",
                issue_type="missing",
                message=f"Applicant folder not found: {wai_folder}",
                severity="error"
            ))
            result.invalid_applicants += 1
            continue
        
        # Count files for statistics
        pdf_files = list(wai_folder.glob("*.pdf"))
        result.total_files_checked += len(pdf_files)
        
        # Scan for issues
        issues = scan_applicant_files(
            wai_folder=wai_folder,
            wai_number=wai_number,
            required_attachments=required_attachments
        )
        
        if issues:
            result.issues.extend(issues)
            if any(i.severity == "error" for i in issues):
                result.invalid_applicants += 1
                if stop_on_first_error:
                    logger.warning(f"Stopping preflight check after first error in {wai_number}")
                    break
            else:
                result.valid_applicants += 1
        else:
            result.valid_applicants += 1
    
    # Log summary
    logger.info(f"Preflight check complete: {result.valid_applicants}/{result.total_applicants} valid")
    if result.issues:
        logger.warning(f"Found {result.error_count} errors, {result.warning_count} warnings")
    
    return result


def print_preflight_report(result: PreflightResult, verbose: bool = False) -> None:
    """Print a formatted preflight report.
    
    Args:
        result: PreflightResult to report on.
        verbose: If True, show all issues. If False, only show errors.
    """
    print(result.summary())
    
    if result.has_errors:
        invalid_wais = result.get_invalid_wai_numbers()
        print(f"\nApplicants with errors ({len(invalid_wais)}):")
        for wai in invalid_wais:
            wai_issues = result.get_issues_for_wai(wai)
            errors = [i for i in wai_issues if i.severity == "error"]
            print(f"  {wai}: {len(errors)} error(s)")
            for issue in errors:
                print(f"    - {issue.file_name}: {issue.message}")

