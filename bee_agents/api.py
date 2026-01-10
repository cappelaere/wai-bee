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
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import argparse
import time

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from fastapi.openapi.utils import get_openapi
from redis import asyncio as aioredis

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

# Import modular routers
from .api_routers import (
    health_router,
    scores_router,
    analysis_router,
    criteria_router,
    admin_router,
    reviews_router,
)

# Configure logging
logger = setup_logging('api')

# Import shared utilities to avoid circular imports
from .api_utils import data_services, get_data_service, get_scholarship_config_path, load_scholarship_config


def load_available_scholarships() -> List[str]:
    """Load available scholarships from WAI-general-2025/config/users.json.
    
    Returns:
        List of enabled scholarship identifiers
    """
    config_path = Path("WAI-general-2025/config/users.json")
    if not config_path.exists():
        logger.warning(f"User config file not found: {config_path}, using defaults")
        return ["Delaney_Wings", "Evans_Wings"]
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        scholarships = config.get("scholarships", {})
        # Return only enabled scholarships
        available = [
            key for key, value in scholarships.items()
            if value.get("enabled", True)
        ]
        
        logger.info(f"Loaded {len(available)} available scholarships from config")
        return available
    except Exception:
        logger.exception("Error loading scholarships from config")
        return ["Delaney_Wings", "Evans_Wings"]


# Load available scholarships dynamically from config
AVAILABLE_SCHOLARSHIPS = load_available_scholarships()

# Note: get_scholarship_config_path and load_scholarship_config are now imported from api_utils


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    initialize_services()
    
    # Initialize Redis cache
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        # Note: decode_responses must be False for fastapi-cache2 to work correctly
        redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=False)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logger.info(f"Redis cache initialized at {redis_url}")
    except Exception:
        logger.exception("Failed to initialize Redis cache. Caching will be disabled.")
    
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

# Allow chat frontend (port 8100) to call admin APIs on this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8100",
        "http://127.0.0.1:8100",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include modular routers
app.include_router(health_router)
app.include_router(scores_router)
app.include_router(analysis_router)
app.include_router(criteria_router)
app.include_router(admin_router)
app.include_router(reviews_router)

logger.info("Modular API routers integrated successfully")


def custom_openapi():
    """Customize OpenAPI schema with bearerAuth and secure review endpoints."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Ensure servers are defined so OpenAPI-based tools know where to call.
    # This is important for the BeeAI OpenAPITool, which requires at least
    # one server URL.
    servers = openapi_schema.get("servers")
    if not servers:
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8200",
                "description": "Development server (default port)",
            }
        ]

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})

    # Define HTTP Bearer auth scheme
    security_schemes["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Use 'Bearer &lt;token&gt;' from the chat /login endpoint.",
    }

    # Mark review endpoints as requiring bearer auth
    paths = openapi_schema.get("paths", {})
    for path, methods in paths.items():
        if path in ("/reviews", "/reviews/me"):
            for method, operation in methods.items():
                if method.lower() in {"get", "post", "put", "delete", "patch", "options", "head"}:
                    security = operation.get("security") or []
                    # Avoid duplicating bearerAuth entries if regeneration happens
                    if not any("bearerAuth" in s for s in security):
                        security.append({"bearerAuth": []})
                    operation["security"] = security

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


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
        except Exception:
            logger.exception("Failed to initialize data service for %s", scholarship_name)
    
    if not data_services:
        raise ValueError("No data services could be initialized")


# Backward compatibility: alias for tests
def initialize_service(scholarship_name: str, base_output_dir: str = "outputs"):
    """Initialize data service for a single scholarship (backward compatibility).
    
    Args:
        scholarship_name: Name of the scholarship
        base_output_dir: Base directory containing output files
    """
    global data_services
    data_services[scholarship_name] = DataService(scholarship_name, base_output_dir)
    logger.info(f"API initialized for scholarship: {scholarship_name}")



@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon."""
    favicon_path = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return JSONResponse(status_code=204, content={})


# REMOVED: Duplicate endpoint - now handled by bee_agents/api_routers/health.py


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

    except Exception as e:
        logger.exception(f"Error getting scholarship info for {scholarship}")
        raise HTTPException(status_code=500, detail=str(e))


def require_admin(request: Request) -> None:
    """Placeholder admin guard for future integration.

    Currently assumes that access to /admin endpoints is restricted by
    deployment (e.g., API gateway, auth middleware).
    """
    return


# REMOVED: Duplicate admin endpoints - now handled by bee_agents/api_routers/admin.py
# The following endpoints are defined in the admin router:
# - GET /admin/{scholarship}/weights
# - PUT /admin/{scholarship}/weights
# - GET /admin/{scholarship}/criteria/{agent_name}
# - PUT /admin/{scholarship}/criteria/{agent_name}
# - POST /admin/{scholarship}/criteria/{agent_name}/regenerate


# REMOVED: Duplicate endpoints - now handled by bee_agents/api_routers/criteria.py
# The following endpoints are defined in the criteria router:
# - GET /criteria (list_criteria)
# - GET /criteria/{scholarship}/{filename} (get_criteria_file)


# REMOVED: Duplicate endpoint - now handled by bee_agents/api_routers/health.py


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


# REMOVED: Duplicate score endpoints - now handled by bee_agents/api_routers/scores.py
# The following endpoints are defined in the scores router:
# - GET /top_scores
# - GET /score
# - GET /statistics


# REMOVED: Duplicate analysis endpoints - now handled by bee_agents/api_routers/analysis.py
# The following endpoints are defined in the analysis router:
# - GET /application
# - GET /academic
# - GET /essay
# - GET /recommendation


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

    except Exception as e:
        logger.exception("Error listing attachments for %s", wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments/text", tags=["Attachments"], response_class=HTMLResponse)
async def download_text_attachment(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number"),
    filename: str = Query(..., description="Text filename (e.g., 101127_30_1.txt)")
):
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
        
  
    except Exception as e:
        logger.exception("Error rendering text file %s for %s", filename, wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments", tags=["Attachments"])
async def download_attachment(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number"),
    filename: str = Query(..., description="PDF filename")
):
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

    except Exception as e:
        logger.exception("Error downloading attachment %s for %s", filename, wai_number)
        raise HTTPException(status_code=500, detail=str(e))


# REMOVED: Second duplicate list_criteria endpoint - now handled by bee_agents/api_routers/criteria.py
# REMOVED: get_criteria endpoint - this was a different implementation not in the router

# Note: The criteria router provides:
# - GET /criteria?scholarship={name} - lists all criteria files
# - GET /criteria/{scholarship}/{filename} - downloads specific criteria file
#
# The old get_criteria endpoint (GET /criteria/{criteria_type}) had a different URL pattern
# and is not currently implemented in the router. If needed, it should be added to the router.

# REMOVED: Legacy /criteria/{criteria_type} endpoint
# Use /criteria/by-type?criteria_type=...&scholarship=... from the criteria router instead


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
 
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing agents.json: {e}")
        raise HTTPException(status_code=500, detail="Invalid agent configuration file")
    except Exception as e:
        logger.exception("Error getting agent configuration for %s", data_service.scholarship_name)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/by-name", tags=["Configuration"])
async def get_agent_config(
    agent_name: str = Query(..., description="Name of the agent (e.g., 'academic', 'essay', 'recommendation')", example="academic"),
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
    
    except json.JSONDecodeError as e:
        logger.exception(f"Error parsing agents.json: {e}")
        raise HTTPException(status_code=500, detail="Invalid agent configuration file")
    except Exception as e:
        logger.exception("Error getting agent configuration for %s", data_service.scholarship_name)
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
