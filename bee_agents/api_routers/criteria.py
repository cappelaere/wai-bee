"""Criteria/Prompts management endpoints.

Returns evaluation prompts generated from config.yml facets.
These prompts are used by agents to evaluate scholarship applications.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Updated: 2026-01-01
Version: 2.0.0
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
    """List all available evaluation prompts for a scholarship.
    
    Returns a list of all prompt files available for the specified scholarship,
    including their names, filenames, and fully qualified download URLs.
    
    **Example Request:**
    ```
    GET /criteria?scholarship=Delaney_Wings
    ```
    
    **Example Response:**
    ```json
    {
      "scholarship": "Delaney_Wings",
      "criteria_count": 4,
      "criteria": [
        {
          "name": "application_analysis",
          "filename": "application_analysis.txt",
          "type": "analysis",
          "agent": "application",
          "url": "http://localhost:8200/criteria/file?scholarship=Delaney_Wings&filename=application_analysis.txt"
        }
      ]
    }
    ```
    
    Args:
        scholarship: Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')
        
    Returns:
        Dictionary containing:
        - scholarship: Name of the scholarship
        - criteria_count: Number of prompt files found
        - criteria: List of prompt objects with name, filename, and download URL
        
    Raises:
        HTTPException 404: If scholarship not found or no prompts directory exists
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    prompts_dir = Path("data") / scholarship / "prompts"
    
    if not prompts_dir.exists():
        logger.warning(f"Prompts directory not found: {prompts_dir}")
        raise HTTPException(
            status_code=404,
            detail=f"No prompts found for scholarship: {scholarship}. Run generate_artifacts.py to create them."
        )
    
    # Get base URL from request
    base_url = str(request.base_url).rstrip('/') if request else "http://localhost:8200"
    
    criteria_files = []
    for file_path in sorted(prompts_dir.glob("*.txt")):
        prompt_name = file_path.stem  # filename without extension
        # Parse agent name and type from filename (e.g., "essay_analysis" -> agent="essay", type="analysis")
        parts = prompt_name.rsplit('_', 1)
        agent_name = parts[0] if len(parts) > 1 else prompt_name
        prompt_type = parts[1] if len(parts) > 1 else "analysis"
        
        criteria_files.append({
            "name": prompt_name,
            "filename": file_path.name,
            "type": prompt_type,
            "agent": agent_name,
            "url": f"{base_url}/criteria/file?scholarship={scholarship}&filename={file_path.name}"
        })
    
    logger.info(f"Listed {len(criteria_files)} prompt files for {scholarship}")
    
    return {
        "scholarship": scholarship,
        "criteria_count": len(criteria_files),
        "criteria": criteria_files
    }


@router.get("/criteria/by-type", operation_id="get_criteria_by_type")
async def get_criteria_by_type(
    criteria_type: str = Query(
        ...,
        description="Type of evaluation criteria (agent name). E.g.: application, resume, essay, recommendation",
        example="essay"
    ),
    scholarship: str = Query(
        ...,
        description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')",
        example="Delaney_Wings"
    )
):
    """Get full evaluation prompt text for a specific agent type.
    
    Retrieves the complete analysis prompt for a given agent type.
    The endpoint maps agent types to their corresponding prompt files:
    - `application` → `application_analysis.txt`
    - `resume` → `resume_analysis.txt`
    - `essay` → `essay_analysis.txt`
    - `recommendation` → `recommendation_analysis.txt`
    
    **Example Request:**
    ```
    GET /criteria/by-type?criteria_type=essay&scholarship=Delaney_Wings
    ```
    
    **Example Response:**
    ```json
    {
      "scholarship": "Delaney_Wings",
      "criteria_type": "essay",
      "filename": "essay_analysis.txt",
      "content": "# Essay Analysis Evaluation Criteria\n\n...",
      "line_count": 57
    }
    ```
    
    Args:
        criteria_type: Agent type (application, resume, essay, recommendation)
        scholarship: Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')
        
    Returns:
        Dictionary containing:
        - scholarship: Name of the scholarship
        - criteria_type: The agent type requested
        - filename: The actual filename
        - content: Full text content of the prompt file
        - line_count: Number of lines in the prompt file
        
    Raises:
        HTTPException 400: If criteria_type is invalid
        HTTPException 404: If scholarship not found or prompt file doesn't exist
    """
    logger.info(f"get_criteria_by_type called: criteria_type='{criteria_type}', scholarship='{scholarship}'")
    
    # Check if criteria_type is a literal template string (client-side error)
    if criteria_type.startswith('{') and criteria_type.endswith('}'):
        logger.error(f"Client sent literal template string '{criteria_type}'")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid criteria_type: '{criteria_type}'. Use an agent name like: application, resume, essay, recommendation"
        )
    
    try:
        get_data_service(scholarship)  # Validate scholarship exists
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating scholarship '{scholarship}': {e}")
        raise HTTPException(status_code=500, detail=f"Error validating scholarship: {str(e)}")
    
    # Valid agent types (dynamically check what prompts exist)
    prompts_dir = Path("data") / scholarship / "prompts"
    if not prompts_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No prompts directory for scholarship: {scholarship}. Run generate_artifacts.py"
        )
    
    # Map type to filename - support both old format (academic) and new format (resume)
    type_mapping = {
        "academic": "resume",  # Legacy mapping
    }
    mapped_type = type_mapping.get(criteria_type, criteria_type)
    
    filename = f"{mapped_type}_analysis.txt"
    criteria_path = prompts_dir / filename
    
    if not criteria_path.exists():
        # List available types
        available = [f.stem.replace('_analysis', '') for f in prompts_dir.glob('*_analysis.txt')]
        raise HTTPException(
            status_code=404,
            detail=f"Prompt not found for '{criteria_type}'. Available types: {', '.join(available)}"
        )
    
    try:
        with open(criteria_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        line_count = len(content.split('\n'))
        logger.info(f"Retrieved {criteria_type} prompt for {scholarship}: {line_count} lines")
        
        return {
            "scholarship": scholarship,
            "criteria_type": criteria_type,
            "filename": filename,
            "content": content,
            "line_count": line_count
        }
    except Exception as e:
        logger.error(f"Error reading prompt {criteria_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read prompt file: {str(e)}")


@router.get("/criteria/file", operation_id="get_criteria_file")
async def get_criteria_file(
    scholarship: str = Query(
        ...,
        description="Name of the scholarship (e.g., 'Delaney_Wings' or 'Evans_Wings')",
        example="Delaney_Wings"
    ),
    filename: str = Query(
        ...,
        description="Name of the prompt file (must end with .txt)",
        example="essay_analysis.txt"
    )
):
    """Download a specific prompt file by filename.
    
    Downloads a prompt file directly as plain text.
    
    **Example Request:**
    ```
    GET /criteria/file?scholarship=Delaney_Wings&filename=essay_analysis.txt
    ```
    
    Args:
        scholarship: Name of the scholarship
        filename: Exact filename of the prompt file (must end with .txt)
        
    Returns:
        FileResponse: Plain text file
        
    Raises:
        HTTPException 400: If filename is invalid
        HTTPException 404: If scholarship not found or prompt file doesn't exist
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    # Validate filename (security: prevent path traversal)
    if not filename.endswith('.txt') or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    prompts_path = Path("data") / scholarship / "prompts" / filename
    
    if not prompts_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Prompt file not found: {filename}"
        )
    
    logger.info(f"Serving prompt file: {scholarship}/{filename}")
    
    return FileResponse(
        path=prompts_path,
        media_type="text/plain",
        filename=filename
    )


# Made with Bob
