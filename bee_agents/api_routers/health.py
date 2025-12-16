"""Health check and status endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


@router.get("/", operation_id="root")
async def root():
    """Root endpoint - API health check."""
    from ..api import data_services
    
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


@router.get("/health", operation_id="health_check")
async def health_check():
    """Health check endpoint for monitoring."""
    from ..api import data_services
    
    if not data_services:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": "No data services initialized"}
        )
    
    return {
        "status": "healthy",
        "scholarships": list(data_services.keys()),
        "total_scholarships": len(data_services)
    }

# Made with Bob
