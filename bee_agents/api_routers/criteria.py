"""Criteria management endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi_cache.decorator import cache
from ..api_utils import get_data_service

router = APIRouter(tags=["Criteria"])
logger = logging.getLogger(__name__)


@router.get("/criteria", operation_id="list_criteria")
@cache(expire=3600)  # Cache for 60 minutes
async def list_criteria(
    request: Request,
    scholarship: str = Query(
        ...,
        description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')",
        example="Delaney_Wings"
    )
):
    """List all available evaluation criteria files for a scholarship.
    
    Returns a list of all criteria files available for the specified scholarship,
    including their names, filenames, and fully qualified download URLs. This endpoint
    is useful for discovering what criteria types are available before requesting
    specific criteria content.
    
    **Example Request:**
    ```
    GET /criteria?scholarship=Delaney_Wings
    ```
    
    **Example Response:**
    ```json
    {
      "scholarship": "Delaney_Wings",
      "criteria_count": 5,
      "criteria": [
        {
          "name": "academic_criteria",
          "filename": "academic_criteria.txt",
          "url": "http://localhost:8200/criteria/Delaney_Wings/academic_criteria.txt"
        },
        {
          "name": "application_criteria",
          "filename": "application_criteria.txt",
          "url": "http://localhost:8200/criteria/Delaney_Wings/application_criteria.txt"
        }
      ]
    }
    ```
    
    Args:
        scholarship: Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')
        
    Returns:
        Dictionary containing:
        - scholarship: Name of the scholarship
        - criteria_count: Number of criteria files found
        - criteria: List of criteria objects with name, filename, and download URL
        
    Raises:
        HTTPException 404: If scholarship not found or no criteria directory exists
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    criteria_dir = Path("data") / scholarship / "criteria"
    
    if not criteria_dir.exists():
        logger.warning(f"Criteria directory not found: {criteria_dir}")
        raise HTTPException(
            status_code=404,
            detail=f"No criteria found for scholarship: {scholarship}"
        )
    
    # Get base URL from request
    base_url = str(request.base_url).rstrip('/') if request else "http://localhost:8200"
    
    criteria_files = []
    for file_path in sorted(criteria_dir.glob("*.txt")):
        criteria_name = file_path.stem  # filename without extension
        criteria_files.append({
            "name": criteria_name,
            "filename": file_path.name,
            "url": f"{base_url}/criteria/file?scholarship={scholarship}&filename={file_path.name}"
        })
    
    logger.info(f"Listed {len(criteria_files)} criteria files for {scholarship}")
    
    return {
        "scholarship": scholarship,
        "criteria_count": len(criteria_files),
        "criteria": criteria_files
    }


@router.get("/criteria/by-type", operation_id="get_criteria_by_type")
async def get_criteria_by_type(
    criteria_type: str = Query(
        ...,
        description="Type of evaluation criteria. Must be one of: application, academic, essay, recommendation, social",
        example="academic"
    ),
    scholarship: str = Query(
        ...,
        description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')",
        example="Delaney_Wings"
    )
):
    """Get full evaluation criteria text for a specific criteria type.
    
    Retrieves the complete evaluation criteria text for a given criteria type.
    The endpoint automatically maps criteria types to their corresponding filenames:
    - `academic` → `academic_criteria.txt`
    - `application` → `application_criteria.txt`
    - `essay` → `essay_criteria.txt`
    - `recommendation` → `recommendation_criteria.txt`
    - `social` → `social_criteria.txt`
    
    **Example Request:**
    ```
    GET /criteria/by-type?criteria_type=academic&scholarship=Delaney_Wings
    ```
    
    **Example Response:**
    ```json
    {
      "scholarship": "Delaney_Wings",
      "criteria_type": "academic",
      "filename": "academic_criteria.txt",
      "content": "# Academic Profile Evaluation Criteria\n\nThis file contains...",
      "line_count": 72
    }
    ```
    
    **Valid Criteria Types:**
    - `application`: Criteria for evaluating application completeness and validity
    - `academic`: Criteria for evaluating academic performance and readiness
    - `essay`: Criteria for evaluating essay quality and content
    - `recommendation`: Criteria for evaluating letters of recommendation
    - `social`: Criteria for evaluating social impact and community involvement
    
    Args:
        criteria_type: Type of criteria. Must be one of: application, academic, essay, recommendation, social
        scholarship: Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')
        
    Returns:
        Dictionary containing:
        - scholarship: Name of the scholarship
        - criteria_type: The criteria type requested
        - filename: The actual filename (e.g., "academic_criteria.txt")
        - content: Full text content of the criteria file
        - line_count: Number of lines in the criteria file
        
    Raises:
        HTTPException 400: If criteria_type is invalid or missing
        HTTPException 404: If scholarship not found or criteria file doesn't exist
        HTTPException 500: If file cannot be read
    """
    logger.info(f"get_criteria_by_type called: criteria_type='{criteria_type}', scholarship='{scholarship}'")
    
    # Check if criteria_type is a literal template string (client-side error)
    if criteria_type.startswith('{') and criteria_type.endswith('}'):
        logger.error(
            f"Client sent literal template string '{criteria_type}' instead of actual criteria type. "
            f"This indicates a client-side URL template substitution issue. "
            f"Expected URL format: /criteria/academic?scholarship=Delaney_Wings"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid criteria_type: '{criteria_type}'. "
                f"It appears you're sending a template variable instead of an actual value. "
                f"Use a valid criteria type: application, academic, essay, recommendation, or social. "
                f"Example: GET /criteria/by-type?criteria_type=academic&scholarship=Delaney_Wings"
            )
        )
    
    try:
        get_data_service(scholarship)  # Validate scholarship exists
        logger.debug(f"Scholarship '{scholarship}' validated successfully")
    except HTTPException as e:
        logger.warning(f"Scholarship validation failed for '{scholarship}': {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error validating scholarship '{scholarship}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validating scholarship: {str(e)}")
    
    # Validate criteria type
    valid_types = ["application", "academic", "essay", "recommendation", "social"]
    logger.debug(f"Validating criteria_type '{criteria_type}' against valid types: {valid_types}")
    
    if criteria_type not in valid_types:
        logger.warning(
            f"Invalid criteria_type '{criteria_type}' provided. "
            f"Valid types are: {', '.join(valid_types)}"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid criteria type '{criteria_type}'. "
                f"Must be one of: {', '.join(valid_types)}. "
                f"Example: GET /criteria/by-type?criteria_type=academic&scholarship=Delaney_Wings"
            )
        )
    
    # Map type to filename
    filename = f"{criteria_type}_criteria.txt"
    criteria_path = Path("data") / scholarship / "criteria" / filename
    logger.debug(f"Mapped criteria_type '{criteria_type}' to filename '{filename}'")
    logger.debug(f"Looking for criteria file at: {criteria_path}")
    
    if not criteria_path.exists():
        logger.warning(
            f"Criteria file not found: {criteria_path} "
            f"(criteria_type='{criteria_type}', scholarship='{scholarship}')"
        )
        raise HTTPException(
            status_code=404,
            detail=f"{criteria_type.title()} criteria not found for {scholarship}"
        )
    
    logger.debug(f"Criteria file found: {criteria_path}")
    
    try:
        with open(criteria_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        line_count = len(content.split('\n'))
        logger.info(
            f"Successfully retrieved {criteria_type} criteria for {scholarship}: "
            f"{line_count} lines, {len(content)} characters"
        )
        
        return {
            "scholarship": scholarship,
            "criteria_type": criteria_type,
            "filename": filename,
            "content": content,
            "line_count": line_count
        }
    except FileNotFoundError:
        logger.error(f"File not found after existence check: {criteria_path}")
        raise HTTPException(status_code=404, detail=f"Criteria file not found: {filename}")
    except PermissionError as e:
        logger.error(f"Permission denied reading criteria file {criteria_path}: {e}")
        raise HTTPException(status_code=500, detail="Permission denied reading criteria file")
    except Exception as e:
        logger.error(
            f"Error reading {criteria_type} criteria for {scholarship} from {criteria_path}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to read criteria file: {str(e)}")


@router.get("/criteria/file", operation_id="get_criteria_file")
async def get_criteria_file(
    scholarship: str = Query(
        ...,
        description="Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')",
        example="Delaney_Wings"
    ),
    filename: str = Query(
        ...,
        description="Name of the criteria file (must end with .txt, e.g., 'academic_criteria.txt')",
        example="academic_criteria.txt"
    )
):
    """Download a specific criteria file by filename.
    
    Downloads a criteria file directly as plain text. This endpoint requires the
    exact filename (e.g., "academic_criteria.txt") rather than just the criteria type.
    Use this endpoint when you already know the exact filename, or use
    `/criteria/by-type` for type-based access.
    
    **Example Request:**
    ```
    GET /criteria/file?scholarship=Delaney_Wings&filename=academic_criteria.txt
    ```
    
    **Security:**
    - Filenames are validated to prevent path traversal attacks
    - Only `.txt` files are allowed
    - Filenames containing `/` or `\` are rejected
    
    Args:
        scholarship: Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')
        filename: Exact filename of the criteria file (must end with .txt, e.g., "academic_criteria.txt")
        
    Returns:
        FileResponse: Plain text file with content-type "text/plain"
        
    Raises:
        HTTPException 400: If filename is invalid (doesn't end with .txt or contains path separators)
        HTTPException 404: If scholarship not found or criteria file doesn't exist
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    # Validate filename (security: prevent path traversal)
    if not filename.endswith('.txt') or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    criteria_path = Path("data") / scholarship / "criteria" / filename
    
    if not criteria_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Criteria file not found: {filename}"
        )
    
    logger.info(f"Serving criteria file: {scholarship}/{filename}")
    
    return FileResponse(
        path=criteria_path,
        media_type="text/plain",
        filename=filename
    )

# Made with Bob
