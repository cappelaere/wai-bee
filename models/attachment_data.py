"""Data models for attachment processing.

This module defines Pydantic models for tracking attachment processing
results, metadata, and errors.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class AttachmentData(BaseModel):
    """Model for processed attachment metadata.
    
    Tracks information about a single processed attachment file including
    source file, output location, text lengths, file sizes, and PII types found.
    
    Attributes:
        wai_number (str): WAI number of the applicant.
        source_file (str): Original filename of the attachment.
        output_file (str): Output filename (.txt).
        source_file_size (int): Size of source file in bytes.
        original_length (int): Character count of original text.
        redacted_length (int): Character count after PII removal.
        pii_types_found (List[str]): Types of PII detected and removed.
        processed_date (datetime): Timestamp when file was processed.
        has_errors (bool): True if processing encountered errors.
        errors (List[str]): List of error messages encountered.
    
    Example:
        >>> data = AttachmentData(
        ...     wai_number="75179",
        ...     source_file="75179_19_1.pdf",
        ...     output_file="75179_19_1.txt",
        ...     source_file_size=245678,
        ...     original_length=5234,
        ...     redacted_length=4891,
        ...     pii_types_found=["names", "emails"],
        ...     processed_date=datetime.now(timezone.utc)
        ... )
    """
    wai_number: str
    source_file: str
    output_file: str
    source_file_size: int = Field(default=0, description="Size of source file in bytes")
    original_length: int
    redacted_length: int
    pii_types_found: List[str] = Field(default_factory=list)
    processed_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    has_errors: bool = Field(default=False, description="True if errors occurred")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class ProcessingError(BaseModel):
    """Model for tracking processing errors.
    
    Attributes:
        wai_number (str): WAI number where error occurred.
        error_message (str): Description of the error.
        source_file (Optional[str]): File that caused the error, if applicable.
    """
    wai_number: str
    error_message: str
    source_file: Optional[str] = None


class AttachmentResult(BaseModel):
    """Model for attachment processing results.
    
    Tracks overall statistics and timing for a batch of attachment processing.
    
    Attributes:
        total (int): Total number of attachments attempted.
        successful (int): Number successfully processed.
        failed (int): Number that failed processing.
        errors (List[ProcessingError]): List of errors encountered.
        start_time (Optional[float]): Processing start timestamp.
        end_time (Optional[float]): Processing end timestamp.
        total_duration (Optional[float]): Total processing time in seconds.
        avg_duration_per_file (Optional[float]): Average time per file.
    
    Example:
        >>> result = AttachmentResult(total=10, successful=9, failed=1)
        >>> result.add_success()
        >>> result.add_error("75179", "Failed to parse file", "doc.pdf")
    """
    total: int
    successful: int
    failed: int
    errors: List[ProcessingError] = Field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    avg_duration_per_file: Optional[float] = None
    
    def add_success(self):
        """Increment successful count."""
        self.successful += 1
    
    def add_error(self, wai_number: str, error_message: str, source_file: Optional[str] = None):
        """Add an error to the results.
        
        Args:
            wai_number (str): WAI number where error occurred.
            error_message (str): Description of the error.
            source_file (Optional[str]): File that caused the error.
        """
        self.failed += 1
        self.errors.append(ProcessingError(
            wai_number=wai_number,
            error_message=error_message,
            source_file=source_file
        ))
    
    def calculate_timing(self):
        """Calculate timing metrics from start and end times."""
        if self.start_time and self.end_time:
            self.total_duration = self.end_time - self.start_time
            if self.total > 0:
                self.avg_duration_per_file = self.total_duration / self.total

# Made with Bob
