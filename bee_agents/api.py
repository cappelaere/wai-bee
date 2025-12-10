"""FastAPI server for scholarship analysis data.

This module provides a REST API for accessing scholarship application
analysis data including scores, statistics, and detailed analyses.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT

Example:
    Run the server::
    
        python -m bee_agents.api --scholarship Delaney_Wings --port 8000
    
    Or use uvicorn directly::
    
        uvicorn bee_agents.api:app --reload --port 8000
"""

import logging
import os
import json
from typing import Optional, List, Dict
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
import argparse
import time

from .data_service import DataService
from .models import (
    ScoreResponse,
    TopScoresResponse,
    StatisticsResponse,
    ApplicationAnalysisResponse,
    AcademicAnalysisResponse,
    EssayAnalysisResponse,
    RecommendationAnalysisResponse,
    ErrorResponse
)
from .logging_config import setup_logging

# Configure logging
logger = setup_logging('api')

# Global data services dictionary (one per scholarship)
data_services: Dict[str, DataService] = {}
AVAILABLE_SCHOLARSHIPS = ["Delaney_Wings", "Evans_Wings"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    initialize_services()
    yield
    # Shutdown (if needed in the future)


# Create FastAPI app
app = FastAPI(
    title="Scholarship Analysis API",
    description="REST API for accessing scholarship application analysis data with multi-tenancy support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    servers=[
        {
            "url": "http://localhost:8200",
            "description": "Development server (default port)"
        }
    ]
)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing information."""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Incoming request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2)
        }
    )
    
    return response


def initialize_services(base_output_dir: str = "outputs"):
    """Initialize data services for all available scholarships.
    
    Args:
        base_output_dir: Base directory containing output files
    """
    global data_services
    
    for scholarship_name in AVAILABLE_SCHOLARSHIPS:
        try:
            data_services[scholarship_name] = DataService(scholarship_name, base_output_dir)
            logger.info(f"API initialized for scholarship: {scholarship_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize data service for {scholarship_name}: {e}")
    
    if not data_services:
        raise ValueError("No data services could be initialized")


def get_data_service(scholarship: str) -> DataService:
    """Get the data service for a specific scholarship.
    
    Args:
        scholarship: Name of the scholarship
        
    Returns:
        DataService instance for the scholarship
        
    Raises:
        HTTPException: If scholarship not found or not available
    """
    if scholarship not in data_services:
        raise HTTPException(
            status_code=404,
            detail=f"Scholarship '{scholarship}' not found. Available: {', '.join(data_services.keys())}"
        )
    return data_services[scholarship]



@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon."""
    favicon_path = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return JSONResponse(status_code=204, content={})


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    if not data_services:
        return JSONResponse(
            status_code=503,
            content={"error": "Service not initialized", "detail": "Data services not configured"}
        )
    return {
        "message": "Scholarship Analysis API",
        "version": "2.0.0",
        "status": "operational",
        "available_scholarships": list(data_services.keys())
    }


@app.get("/scholarship", tags=["Scholarship"])
async def get_scholarship_info(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """Get scholarship information and details.
    
    Args:
        scholarship: Name of the scholarship
    
    Returns:
        Dictionary containing scholarship name, description, eligibility,
        requirements, and other relevant information
    """
    data_service = get_data_service(scholarship)
    
    try:
        scholarship_info = data_service.load_scholarship_info()
        if not scholarship_info:
            raise HTTPException(
                status_code=404,
                detail=f"Scholarship information not found for {scholarship}"
            )
        
        return scholarship_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scholarship info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/criteria", tags=["Criteria"])
async def list_criteria(
    request: Request,
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """List all available criteria files for a scholarship with fully qualified URLs.
    
    Args:
        scholarship: Name of the scholarship
        
    Returns:
        Dictionary with list of criteria and their download URLs
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
            "url": f"{base_url}/criteria/{scholarship}/{file_path.name}"
        })
    
    logger.info(f"Listed {len(criteria_files)} criteria files for {scholarship}")
    
    return {
        "scholarship": scholarship,
        "criteria_count": len(criteria_files),
        "criteria": criteria_files
    }


@app.get("/criteria/{scholarship}/{filename}", tags=["Criteria"])
async def get_criteria_file(
    scholarship: str,
    filename: str
):
    """Download a specific criteria file.
    
    Args:
        scholarship: Name of the scholarship
        filename: Criteria filename (e.g., 'academic_criteria.txt')
        
    Returns:
        File content as plain text
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    criteria_file = Path("data") / scholarship / "criteria" / filename
    
    if not criteria_file.exists() or not criteria_file.suffix == '.txt':
        logger.warning(f"Criteria file not found: {criteria_file}")
        raise HTTPException(
            status_code=404,
            detail=f"Criteria file not found: {filename}"
        )
    
    logger.info(f"Serving criteria file: {scholarship}/{filename}")
    
    return FileResponse(
        criteria_file,
        media_type="text/plain",
        filename=filename
    )


@app.get("/health", tags=["Health"])
async def health_check(
    scholarship: Optional[str] = Query(None, description="Scholarship name (optional)")
):
    """Health check endpoint. Optionally check a specific scholarship.
    
    Args:
        scholarship: Name of the scholarship (optional)
    """
    if scholarship:
        # Check specific scholarship
        data_service = get_data_service(scholarship)
        return {
            "status": "healthy",
            "scholarship": data_service.scholarship_name,
            "total_applications": len(data_service.get_all_wai_numbers())
        }
    else:
        # General health check
        return {
            "status": "healthy",
            "available_scholarships": list(data_services.keys()),
            "total_scholarships": len(data_services)
        }


@app.get("/openapi.yml", tags=["Documentation"])
async def get_openapi_yaml():
    """Download OpenAPI specification as YAML file."""
    openapi_file = Path(__file__).parent / "openapi.yml"
    if not openapi_file.exists():
        raise HTTPException(
            status_code=404,
            detail="OpenAPI spec not found. Run: python -m bee_agents.generate_openapi"
        )
    return FileResponse(
        openapi_file,
        media_type="application/x-yaml",
        filename="openapi.yml"
    )


@app.get("/openapi.json", tags=["Documentation"])
async def get_openapi_json():
    """Download OpenAPI specification as JSON file."""
    openapi_file = Path(__file__).parent / "openapi.json"
    if not openapi_file.exists():
        raise HTTPException(
            status_code=404,
            detail="OpenAPI spec not found. Run: python -m bee_agents.generate_openapi"
        )
    return FileResponse(
        openapi_file,
        media_type="application/json",
        filename="openapi.json"
    )


@app.get("/top_scores", response_model=TopScoresResponse, tags=["Scores"])
async def get_top_scores(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    limit: int = Query(10, ge=1, le=100, description="Number of top scores to return")
):
    """Get top scoring applications for a specific scholarship.
    
    Args:
        scholarship: Name of the scholarship
        limit: Maximum number of results to return (1-100)
        
    Returns:
        TopScoresResponse with list of top scoring applications
    """
    data_service = get_data_service(scholarship)
    
    try:
        top_scores = data_service.get_top_scores(limit)
        return TopScoresResponse(
            scholarship=data_service.scholarship_name,
            total_applications=len(data_service.get_all_wai_numbers()),
            top_scores=[ScoreResponse(**score) for score in top_scores]
        )
    except Exception as e:
        logger.error(f"Error getting top scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/score", response_model=ScoreResponse, tags=["Scores"])
async def get_individual_score(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get score for a specific application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        ScoreResponse with application scores and applicant information
    """
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_application_analysis(wai_number)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Application {wai_number} not found")
        
        # Load applicant data
        app_data = data_service.load_application_data(wai_number)
        
        return ScoreResponse(
            wai_number=wai_number,
            name=app_data.get('name') if app_data else None,
            city=app_data.get('city') if app_data else None,
            state=app_data.get('state') if app_data else None,
            country=app_data.get('country') if app_data else None,
            overall_score=analysis['scores']['overall_score'],
            completeness_score=analysis['scores']['completeness_score'],
            validity_score=analysis['scores']['validity_score'],
            attachment_score=analysis['scores']['attachment_score'],
            summary=analysis['summary']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting score for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics", response_model=StatisticsResponse, tags=["Statistics"])
async def get_statistics(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """Get statistics for all applications in a specific scholarship.
    
    Args:
        scholarship: Name of the scholarship
    
    Returns:
        StatisticsResponse with aggregated statistics
    """
    data_service = get_data_service(scholarship)
    
    try:
        logger.info(f"Fetching statistics for scholarship: {scholarship}")
        stats = data_service.get_statistics()
        
        if not stats:
            logger.warning(f"No statistics data returned for {scholarship}")
            raise HTTPException(
                status_code=404,
                detail=f"No statistics available for scholarship: {scholarship}"
            )
        
        response_data = StatisticsResponse(
            scholarship=data_service.scholarship_name,
            **stats
        )
        
        logger.info(
            f"Statistics retrieved for {scholarship}: "
            f"total_apps={stats.get('total_applications', 0)}, "
            f"avg_score={stats.get('average_score', 0):.2f}, "
            f"median={stats.get('median_score', 0):.2f}, "
            f"min={stats.get('min_score', 0)}, "
            f"max={stats.get('max_score', 0)}"
        )
        logger.debug(f"Full response data: {response_data.model_dump()}")
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting statistics for {scholarship}: {e}",
            extra={
                "scholarship": scholarship,
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/application", response_model=ApplicationAnalysisResponse, tags=["Analysis"])
async def get_application_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get detailed application analysis.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        ApplicationAnalysisResponse with detailed analysis
    """
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_application_analysis(wai_number)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Application {wai_number} not found")
        
        return ApplicationAnalysisResponse(**analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application analysis for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/academic", response_model=AcademicAnalysisResponse, tags=["Analysis"])
async def get_academic_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get academic analysis for an application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        AcademicAnalysisResponse with academic analysis
    """
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_academic_analysis(wai_number)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Academic analysis for {wai_number} not found"
            )
        
        return AcademicAnalysisResponse(**analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting academic analysis for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/essay", tags=["Analysis"])
async def get_essay_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get combined essay analysis for an application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        Combined analysis of all essays
    """
    data_service = get_data_service(scholarship)
    
    try:
        combined = data_service.load_combined_essay_analysis(wai_number)
        if not combined:
            raise HTTPException(
                status_code=404,
                detail=f"No essay analyses found for {wai_number}"
            )
        
        return combined
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting essay analyses for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendation", tags=["Analysis"])
async def get_recommendation_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get combined recommendation analysis for an application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        Combined analysis of all recommendations
    """
    data_service = get_data_service(scholarship)
    
    try:
        combined = data_service.load_combined_recommendation_analysis(wai_number)
        if not combined:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendation analyses found for {wai_number}"
            )
        
        return combined
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendation analyses for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments", tags=["Attachments"])
async def list_attachments(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """List all attachment files for an application with processing metadata.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        Attachment files with download URLs and processing information
    """
    data_service = get_data_service(scholarship)
    
    try:
        result = data_service.list_attachments(wai_number)
        if not result["files"]:
            raise HTTPException(
                status_code=404,
                detail=f"No attachments found for {wai_number}"
            )
        
        return {
            "wai_number": wai_number,
            "count": len(result["files"]),
            "files": result["files"],
            "processing_summary": result["processing_summary"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing attachments for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments/text/{scholarship}/{wai_number}/{filename}", tags=["Attachments"], response_class=HTMLResponse)
async def download_text_attachment(scholarship: str, wai_number: str, filename: str):
    """View a processed text attachment file in browser with styling.
    
    Args:
        scholarship: Scholarship name
        wai_number: WAI application number
        filename: Text filename (e.g., 101127_30_1.txt)
        
    Returns:
        HTML page with styled text content
    """
    data_service = get_data_service(scholarship)
    
    try:
        # Text files are in outputs/{scholarship}/{wai_number}/attachments/
        file_path = Path("outputs") / scholarship / wai_number / "attachments" / filename
        
        if not file_path.exists() or file_path.suffix.lower() != '.txt':
            raise HTTPException(
                status_code=404,
                detail=f"Text file {filename} not found for {wai_number}"
            )
        
        # Read the text content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get file metadata
        file_size = file_path.stat().st_size
        
        # Create HTML response with styling
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - {wai_number}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        
        .header .meta {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .header .meta span {{
            margin-right: 20px;
        }}
        
        .toolbar {{
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .toolbar button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }}
        
        .toolbar button:hover {{
            background: #764ba2;
        }}
        
        .content {{
            padding: 30px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #333;
            background: #fafafa;
            border-left: 3px solid #667eea;
            margin: 20px;
            border-radius: 6px;
        }}
        
        .footer {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            font-size: 13px;
            color: #666;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
                border-radius: 0;
            }}
            
            .toolbar {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 {filename}</h1>
            <div class="meta">
                <span>📋 WAI: {wai_number}</span>
                <span>📊 Size: {file_size:,} bytes</span>
                <span>🏫 {scholarship}</span>
            </div>
        </div>
        
        <div class="toolbar">
            <div>
                <strong>Processed Text Document</strong>
            </div>
            <div>
                <button onclick="window.print()">🖨️ Print</button>
                <button onclick="downloadRaw()">⬇️ Download</button>
            </div>
        </div>
        
        <div class="content">{content}</div>
        
        <div class="footer">
            <p>This document has been processed for PII redaction and text extraction.</p>
            <p>Original source: {filename.replace('.txt', '.pdf')}</p>
        </div>
    </div>
    
    <script>
        function downloadRaw() {{
            const content = document.querySelector('.content').textContent;
            const blob = new Blob([content], {{ type: 'text/plain' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{filename}';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering text file {filename} for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments/{scholarship}/{wai_number}/{filename}", tags=["Attachments"])
async def download_attachment(scholarship: str, wai_number: str, filename: str):
    """Download original PDF attachment file (admin only).
    
    Args:
        scholarship: Scholarship name
        wai_number: WAI application number
        filename: PDF filename
        
    Returns:
        PDF file download response
    """
    data_service = get_data_service(scholarship)
    
    try:
        file_path = data_service.get_attachment_path(wai_number, filename)
        if not file_path:
            raise HTTPException(
                status_code=404,
                detail=f"Attachment {filename} not found for {wai_number}"
            )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading attachment {filename} for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/criteria", tags=["Criteria"])
async def list_criteria(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """List all available evaluation criteria for the scholarship.
    
    Args:
        scholarship: Name of the scholarship
    
    Returns:
        List of available criteria types with descriptions
    """
    data_service = get_data_service(scholarship)
    
    try:
        criteria_dir = Path("data") / data_service.scholarship_name / "criteria"
        
        if not criteria_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Criteria directory not found for {data_service.scholarship_name}"
            )
        
        criteria_files = []
        criteria_types = {
            "application_criteria.txt": {
                "name": "Application Criteria",
                "description": "Criteria for evaluating application completeness and validity"
            },
            "academic_criteria.txt": {
                "name": "Academic Criteria",
                "description": "Criteria for evaluating academic performance and readiness"
            },
            "essay_criteria.txt": {
                "name": "Essay Criteria",
                "description": "Criteria for evaluating essay quality and content"
            },
            "recommendation_criteria.txt": {
                "name": "Recommendation Criteria",
                "description": "Criteria for evaluating letters of recommendation"
            },
            "social_criteria.txt": {
                "name": "Social Criteria",
                "description": "Criteria for evaluating social impact and community involvement"
            }
        }
        
        for filename, info in criteria_types.items():
            file_path = criteria_dir / filename
            if file_path.exists():
                criteria_files.append({
                    "type": filename.replace("_criteria.txt", ""),
                    "name": info["name"],
                    "description": info["description"],
                    "filename": filename,
                    "url": f"/criteria/{filename.replace('_criteria.txt', '')}"
                })
        
        return {
            "scholarship": data_service.scholarship_name,
            "criteria_count": len(criteria_files),
            "criteria": criteria_files
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/criteria/{criteria_type}", tags=["Criteria"])
async def get_criteria(
    criteria_type: str,
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """Get evaluation criteria for a specific type.
    
    Args:
        criteria_type: Type of criteria (application, academic, essay, recommendation, social)
        scholarship: Name of the scholarship
        
    Returns:
        Criteria content as text
    """
    data_service = get_data_service(scholarship)
    
    # Validate criteria type
    valid_types = ["application", "academic", "essay", "recommendation", "social"]
    if criteria_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid criteria type. Must be one of: {', '.join(valid_types)}"
        )
    
    try:
        criteria_file = Path("data") / data_service.scholarship_name / "criteria" / f"{criteria_type}_criteria.txt"
        
        if not criteria_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"{criteria_type.title()} criteria not found for {data_service.scholarship_name}"
            )
        
        with open(criteria_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "scholarship": data_service.scholarship_name,
            "criteria_type": criteria_type,
            "filename": f"{criteria_type}_criteria.txt",
            "content": content,
            "line_count": len(content.split('\n'))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting {criteria_type} criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", tags=["Configuration"])
async def get_agents_config(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """Get agent configuration and scoring weights for the scholarship.
    
    Args:
        scholarship: Name of the scholarship
    
    Returns:
        Agent configuration including scoring weights and evaluation details
    """
    data_service = get_data_service(scholarship)
    
    try:
        agents_file = Path("data") / data_service.scholarship_name / "agents.json"
        
        if not agents_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Agent configuration not found for {data_service.scholarship_name}"
            )
        
        with open(agents_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return config
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing agents.json: {e}")
        raise HTTPException(status_code=500, detail="Invalid agent configuration file")
    except Exception as e:
        logger.error(f"Error getting agent configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_name}", tags=["Configuration"])
async def get_agent_config(
    agent_name: str,
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """Get configuration for a specific agent.
    
    Args:
        agent_name: Name of the agent (application, academic, essay, recommendation, attachment)
        scholarship: Name of the scholarship
        
    Returns:
        Agent configuration details including weight and evaluation criteria
    """
    data_service = get_data_service(scholarship)
    
    try:
        agents_file = Path("data") / data_service.scholarship_name / "agents.json"
        
        if not agents_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Agent configuration not found for {data_service.scholarship_name}"
            )
        
        with open(agents_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Find the agent
        agent = None
        for a in config.get("agents", []):
            if a.get("name") == agent_name:
                agent = a
                break
        
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found in configuration"
            )
        
        return {
            "scholarship": data_service.scholarship_name,
            "agent": agent
        }
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing agents.json: {e}")
        raise HTTPException(status_code=500, detail="Invalid agent configuration file")
    except Exception as e:
        logger.error(f"Error getting agent configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point for running the API server."""
    parser = argparse.ArgumentParser(description="Scholarship Analysis API Server (Multi-Tenancy)")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Base output directory (default: outputs)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8200,
        help="Port to bind to (default: 8200)"
    )
    
    args = parser.parse_args()
    
    # Initialize all data services (multi-tenancy)
    initialize_services(args.output_dir)
    
    # Run the server
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

# Made with Bob
