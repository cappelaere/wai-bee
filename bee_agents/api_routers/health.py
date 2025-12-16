"""Health check and status endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


def check_disk_space(path: str = ".") -> Dict[str, Any]:
    """Check available disk space."""
    try:
        stat = shutil.disk_usage(path)
        total_gb = stat.total / (1024**3)
        used_gb = stat.used / (1024**3)
        free_gb = stat.free / (1024**3)
        percent_used = (stat.used / stat.total) * 100
        
        return {
            "status": "healthy" if percent_used < 90 else "warning",
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent_used": round(percent_used, 2)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_data_directories() -> Dict[str, Any]:
    """Check if required data directories exist."""
    try:
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        outputs_dir = Path(os.getenv("OUTPUTS_DIR", "outputs"))
        
        return {
            "status": "healthy" if data_dir.exists() and outputs_dir.exists() else "warning",
            "data_dir_exists": data_dir.exists(),
            "outputs_dir_exists": outputs_dir.exists(),
            "data_dir_path": str(data_dir),
            "outputs_dir_path": str(outputs_dir)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_config_files() -> Dict[str, Any]:
    """Check if required configuration files exist."""
    try:
        user_config = Path(os.getenv("USER_CONFIG_FILE", "config/users.json"))
        
        return {
            "status": "healthy" if user_config.exists() else "warning",
            "user_config_exists": user_config.exists(),
            "user_config_path": str(user_config)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    """Enhanced health check endpoint with dependency verification.
    
    Returns detailed health status including:
    - Data services status
    - Disk space availability
    - Directory existence
    - Configuration files
    - Overall system health
    """
    from ..api import data_services
    
    # Check data services
    services_status = "healthy" if data_services else "unhealthy"
    
    # Check dependencies
    disk_check = check_disk_space()
    dirs_check = check_data_directories()
    config_check = check_config_files()
    
    # Determine overall status
    checks = {
        "data_services": {
            "status": services_status,
            "scholarships": list(data_services.keys()) if data_services else [],
            "total_scholarships": len(data_services) if data_services else 0
        },
        "disk_space": disk_check,
        "directories": dirs_check,
        "configuration": config_check
    }
    
    # Overall status is healthy only if all checks pass
    all_healthy = all(
        check.get("status") == "healthy"
        for check in checks.values()
    )
    
    overall_status = "healthy" if all_healthy else "degraded"
    status_code = 200 if all_healthy else 503
    
    response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    }
    
    return JSONResponse(
        status_code=status_code,
        content=response
    )

# Made with Bob
