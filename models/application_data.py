"""Data models for scholarship application processing.

This module defines Pydantic models for representing scholarship application
data, processing results, and errors. These models provide data validation
and serialization capabilities.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Classes:
    ApplicationData: Model for extracted applicant information.
    ProcessingError: Model for tracking processing errors.
    ProcessingResult: Model for overall processing statistics and results.

Example:
    Creating application data::

        from models.application_data import ApplicationData
        
        app_data = ApplicationData(
            wai_number="75179",
            name="John Doe",
            city="Boston",
            country="United States",
            source_file="75179_19.pdf"
        )
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ApplicationData(BaseModel):
    """Model for extracted scholarship application data.
    
    Represents the structured information extracted from a scholarship
    application document, including applicant details and metadata.
    
    Attributes:
        wai_number (str): WAI number of the applicant (unique identifier).
        name (str): Full name of the applicant.
        city (str): City of residence.
        state (Optional[str]): State of residence (for US applicants only).
        country (str): Country of residence.
        source_file (str): Name of the source application file.
        processed_date (str): ISO 8601 timestamp when the application was
            processed. Automatically set to current UTC time.
        validation_errors (List[str]): List of validation errors found.
        has_errors (bool): True if validation errors exist.
    
    Example:
        >>> app_data = ApplicationData(
        ...     wai_number="75179",
        ...     name="Jane Smith",
        ...     city="New York",
        ...     state="NY",
        ...     country="United States",
        ...     source_file="75179_19.pdf"
        ... )
        >>> print(app_data.name)
        'Jane Smith'
    """
    
    wai_number: str = Field(..., description="WAI number of the applicant")
    name: str = Field(..., description="Full name of the applicant")
    city: str = Field(..., description="City of residence")
    state: Optional[str] = Field(default=None, description="State of residence (for US applicants)")
    country: str = Field(..., description="Country of residence")
    source_file: str = Field(..., description="Source application file name")
    processed_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp when processed"
    )
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    has_errors: bool = Field(default=False, description="True if validation errors exist")
    attachment_files_checked: List[dict] = Field(default_factory=list, description="List of attachment files checked with details")
    
    def validate_required_fields(self, attachment_file_details: Optional[List[dict]] = None) -> None:
        """Validate that all required fields and attachments are present and valid.
        
        Checks that name, city, and country are not "Unknown" or empty.
        Checks that required attachment files exist and are non-empty.
        Updates validation_errors, has_errors, and attachment_files_checked fields.
        
        Args:
            attachment_file_details: List of dicts with file info:
                [{"name": str, "size": int, "valid": bool, "error": str}, ...]
        """
        errors = []
        
        # Check name
        if not self.name or self.name.strip() == "" or self.name == "Unknown":
            errors.append("Name is missing or Unknown")
        
        # Check city
        if not self.city or self.city.strip() == "" or self.city == "Unknown":
            errors.append("City is missing or Unknown")
        
        # Check country
        if not self.country or self.country.strip() == "" or self.country == "Unknown":
            errors.append("Country is missing or Unknown")
        
        # Check state for US applicants
        if self.country and "United States" in self.country:
            if not self.state or self.state == "Unknown":
                errors.append("State is required for US applicants but is missing or Unknown")
        
        # Check required attachments (if provided)
        if attachment_file_details is not None:
            self.attachment_files_checked = attachment_file_details
            
            required_count = 5  # Recommendation #1, #2, Resume, Essay #1, #2
            valid_files = [f for f in attachment_file_details if f.get('valid', False)]
            actual_count = len(valid_files)
            
            if actual_count < required_count:
                errors.append(f"Required {required_count} valid attachment files, but found only {actual_count}")
            
            # Report specific file errors
            for file_info in attachment_file_details:
                if not file_info.get('valid', False):
                    file_error = file_info.get('error', 'Unknown error')
                    file_name = file_info.get('name', 'Unknown file')
                    file_size = file_info.get('size', 0)
                    errors.append(f"File '{file_name}' (size: {file_size} bytes): {file_error}")
        
        self.validation_errors = errors
        self.has_errors = len(errors) > 0


class ProcessingError(BaseModel):
    """Model for tracking processing errors.
    
    Captures information about errors that occur during application processing,
    including the WAI number, error message, and optional source file.
    
    Attributes:
        wai_number (str): WAI number of the application that failed.
        error_message (str): Description of the error that occurred.
        source_file (Optional[str]): Name of the source file if applicable.
            Defaults to None.
    
    Example:
        >>> error = ProcessingError(
        ...     wai_number="75179",
        ...     error_message="Failed to parse document",
        ...     source_file="75179_19.pdf"
        ... )
    """
    
    wai_number: str
    error_message: str
    source_file: Optional[str] = None


class ProcessingResult(BaseModel):
    """Model for overall processing results and statistics.
    
    Tracks the results of processing multiple scholarship applications,
    including success/failure counts, errors, and timing metrics.
    
    Attributes:
        total (int): Total number of applications attempted.
        successful (int): Number of successfully processed applications.
        failed (int): Number of failed applications.
        errors (List[ProcessingError]): List of errors encountered during
            processing. Defaults to empty list.
        start_time (Optional[float]): Processing start time as Unix timestamp.
            Defaults to None.
        end_time (Optional[float]): Processing end time as Unix timestamp.
            Defaults to None.
        total_duration (Optional[float]): Total processing duration in seconds.
            Calculated by calculate_timing(). Defaults to None.
        avg_duration_per_app (Optional[float]): Average duration per application
            in seconds. Calculated by calculate_timing(). Defaults to None.
    
    Example:
        >>> result = ProcessingResult(total=10, successful=0, failed=0)
        >>> result.add_success()
        >>> result.add_error("75179", "Parse failed", "75179_19.pdf")
        >>> result.calculate_timing()
        >>> print(f"Success rate: {result.successful}/{result.total}")
    """
    
    total: int = Field(..., description="Total applications attempted")
    successful: int = Field(..., description="Successfully processed applications")
    failed: int = Field(..., description="Failed applications")
    errors: List[ProcessingError] = Field(default_factory=list, description="List of errors")
    start_time: Optional[float] = Field(default=None, description="Processing start time (timestamp)")
    end_time: Optional[float] = Field(default=None, description="Processing end time (timestamp)")
    total_duration: Optional[float] = Field(default=None, description="Total processing duration in seconds")
    avg_duration_per_app: Optional[float] = Field(default=None, description="Average duration per application in seconds")
    
    def add_success(self):
        """Increment the successful application count.
        
        Increases the successful counter by one. Should be called when
        an application is processed successfully.
        """
        self.successful += 1
    
    def add_error(self, wai_number: str, error_message: str, source_file: Optional[str] = None):
        """Add an error to the results.
        
        Records a processing error and increments the failed counter.
        
        Args:
            wai_number (str): WAI number of the failed application.
            error_message (str): Description of the error.
            source_file (Optional[str]): Source file name if applicable.
                Defaults to None.
        """
        self.failed += 1
        self.errors.append(
            ProcessingError(
                wai_number=wai_number,
                error_message=error_message,
                source_file=source_file
            )
        )
    
    def calculate_timing(self):
        """Calculate timing metrics after processing is complete.
        
        Computes total_duration and avg_duration_per_app based on
        start_time and end_time. Should be called after processing
        is finished.
        
        Note:
            Requires both start_time and end_time to be set. If total is 0,
            avg_duration_per_app will not be calculated.
        """
        if self.start_time and self.end_time:
            self.total_duration = self.end_time - self.start_time
            if self.total > 0:
                self.avg_duration_per_app = self.total_duration / self.total

# Made with Bob
