"""Admin configuration endpoints for scholarship management.

Read-only access to scholarship configuration. All changes must be made
through config.yml and regenerated using generate_artifacts.py.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-17
Version: 1.1.0
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie, Depends

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


def require_admin(auth_token: Optional[str] = Cookie(None)) -> dict:
    """Admin guard for admin endpoints."""
    from ..auth import verify_token_with_context
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token_data


@router.get("/{scholarship}/prompts/{agent}", operation_id="get_agent_prompts")
async def get_prompts(
    scholarship: str,
    agent: str,
    token_data: dict = Depends(require_admin)
):
    """Get analysis and repair prompts for a specific agent (read-only).
    
    Returns both the analysis and repair prompt texts.
    Note: Prompts are generated from config.yml - to modify, update config.yml
    and run generate_artifacts.py.
    """
    try:
        prompts_dir = Path("data") / scholarship / "prompts"
        analysis_path = prompts_dir / f"{agent}_analysis.txt"
        repair_path = prompts_dir / f"{agent}_repair.txt"
        
        result = {}
        
        if analysis_path.exists():
            with open(analysis_path, "r", encoding="utf-8") as f:
                result["analysis_prompt"] = f.read()
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis prompt not found: {analysis_path}"
            )
        
        if repair_path.exists():
            with open(repair_path, "r", encoding="utf-8") as f:
                result["repair_prompt"] = f.read()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompts for {scholarship}/{agent}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scholarship}/scholarship", operation_id="get_scholarship_info")
async def get_scholarship_info(
    scholarship: str,
    token_data: dict = Depends(require_admin)
):
    """Get scholarship.json configuration.
    
    Returns the generated scholarship configuration.
    """
    try:
        scholarship_path = Path("data") / scholarship / "scholarship.json"
        
        if not scholarship_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"scholarship.json not found: {scholarship_path}"
            )
        
        with open(scholarship_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scholarship info for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scholarship}/agents", operation_id="get_agents_config")
async def get_agents_config(
    scholarship: str,
    token_data: dict = Depends(require_admin)
):
    """Get agents.json configuration.
    
    Returns the generated agents configuration.
    """
    try:
        agents_path = Path("data") / scholarship / "agents.json"
        
        if not agents_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"agents.json not found: {agents_path}"
            )
        
        with open(agents_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agents config for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Made with Bob