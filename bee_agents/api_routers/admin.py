"""Admin endpoints for scholarship configuration management (read-only).

All configuration changes must be made through config.yml and regenerated
using generate_artifacts.py. This router provides read-only access to
the generated configuration files.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Updated: 2026-01-01
Version: 2.0.0
License: MIT
"""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query, Request

router = APIRouter(tags=["Admin"], prefix="/admin")
logger = logging.getLogger(__name__)


def require_admin(request: Request) -> None:
    """Placeholder admin guard for future integration.

    Currently assumes that access to /admin endpoints is restricted by
    deployment (e.g., API gateway, auth middleware).
    """
    return


def get_scholarship_path(scholarship: str) -> Path:
    """Get path to scholarship data directory."""
    path = Path("data") / scholarship
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Scholarship not found: {scholarship}")
    return path


@router.get("/scholarship", operation_id="get_scholarship_config")
async def get_scholarship_config(
    scholarship: str = Query(..., description="Scholarship name", example="Delaney_Wings"),
    _: None = Depends(require_admin),
):
    """Get scholarship.json configuration (read-only).
    
    Returns the generated scholarship configuration including:
    - Scholarship metadata
    - Eligibility requirements
    - Submission requirements
    - Scoring configuration
    - Aggregation weights
    
    Note: To modify configuration, edit config.yml and run generate_artifacts.py
    """
    scholarship_path = get_scholarship_path(scholarship)
    scholarship_file = scholarship_path / "scholarship.json"
    
    if not scholarship_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"scholarship.json not found. Run generate_artifacts.py for {scholarship}"
        )
    
    try:
        with open(scholarship_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading scholarship.json for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", operation_id="get_agents_config")
async def get_agents_config(
    scholarship: str = Query(..., description="Scholarship name", example="Delaney_Wings"),
    _: None = Depends(require_admin),
):
    """Get agents.json configuration (read-only).
    
    Returns the generated agent configuration including:
    - All agent definitions
    - Scoring weights
    - Input file mappings
    - Schema and prompt paths
    
    Note: To modify configuration, edit config.yml and run generate_artifacts.py
    """
    scholarship_path = get_scholarship_path(scholarship)
    agents_file = scholarship_path / "agents.json"
    
    if not agents_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"agents.json not found. Run generate_artifacts.py for {scholarship}"
        )
    
    try:
        with open(agents_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading agents.json for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weights", operation_id="get_weights")
async def get_scholarship_weights(
    scholarship: str = Query(..., description="Scholarship name", example="Delaney_Wings"),
    _: None = Depends(require_admin),
):
    """Get current scoring weights for a scholarship (read-only).
    
    Returns weights extracted from agents.json.
    
    Note: To modify weights, edit config.yml and run generate_artifacts.py
    """
    scholarship_path = get_scholarship_path(scholarship)
    agents_file = scholarship_path / "agents.json"
    
    if not agents_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"agents.json not found. Run generate_artifacts.py for {scholarship}"
        )
    
    try:
        with open(agents_file, 'r', encoding='utf-8') as f:
            agents_config = json.load(f)
        
        weights = {}
        for agent in agents_config.get('agents', []):
            if agent.get('weight') is not None:
                weights[agent['name']] = {
                    "weight": agent['weight'],
                    "description": agent.get('description', ''),
                    "enabled": agent.get('enabled', True),
                }
        
        return {
            "scholarship": scholarship,
            "weights": weights,
            "total_weight": agents_config.get('total_weight', 1.0),
            "scoring_agents": agents_config.get('scoring_agents', []),
            "note": "Read-only. Edit config.yml and run generate_artifacts.py to modify."
        }
    except Exception as e:
        logger.error(f"Error loading weights for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{agent_name}", operation_id="get_agent_prompts")
async def get_agent_prompts(
    scholarship: str = Query(..., description="Scholarship name", example="Delaney_Wings"),
    agent_name: str = "essay",
    _: None = Depends(require_admin),
):
    """Get analysis and repair prompts for an agent (read-only).
    
    Returns both the analysis prompt and repair prompt texts.
    
    Note: Prompts are generated from config.yml facets. To modify,
    edit config.yml and run generate_artifacts.py
    """
    scholarship_path = get_scholarship_path(scholarship)
    prompts_dir = scholarship_path / "prompts"
    
    analysis_path = prompts_dir / f"{agent_name}_analysis.txt"
    repair_path = prompts_dir / f"{agent_name}_repair.txt"
    
    result = {
        "scholarship": scholarship,
        "agent": agent_name,
        "note": "Read-only. Edit config.yml and run generate_artifacts.py to modify."
    }
    
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            result["analysis_prompt"] = f.read()
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis prompt not found for agent: {agent_name}"
        )
    
    if repair_path.exists():
        with open(repair_path, 'r', encoding='utf-8') as f:
            result["repair_prompt"] = f.read()
    
    return result


@router.get("/schema/{agent_name}", operation_id="get_agent_schema")
async def get_agent_schema(
    scholarship: str = Query(..., description="Scholarship name", example="Delaney_Wings"),
    agent_name: str = "essay",
    _: None = Depends(require_admin),
):
    """Get output schema for an agent (read-only).
    
    Returns the JSON schema used to validate agent output.
    
    Note: Schemas are generated from config.yml facets. To modify,
    edit config.yml and run generate_artifacts.py
    """
    scholarship_path = get_scholarship_path(scholarship)
    schema_path = scholarship_path / "schemas_generated" / f"{agent_name}_analysis.schema.json"
    
    if not schema_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Schema not found for agent: {agent_name}"
        )
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        return {
            "scholarship": scholarship,
            "agent": agent_name,
            "schema": schema,
            "note": "Read-only. Edit config.yml and run generate_artifacts.py to modify."
        }
    except Exception as e:
        logger.error(f"Error loading schema for {scholarship}/{agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Made with Bob
