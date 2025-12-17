"""Admin configuration endpoints for scholarship management.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-17
Version: 1.0.0
License: MIT
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Cookie, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


class WeightsUpdate(BaseModel):
    """Model for updating scoring weights."""
    weights: Dict[str, Dict[str, float]]


class CriteriaUpdate(BaseModel):
    """Model for updating criteria text."""
    criteria_text: str


class CriteriaRegenerateRequest(BaseModel):
    """Model for regenerating criteria with LLM."""
    base_description: Optional[str] = ""
    target_model: Optional[str] = None


class PipelineRunRequest(BaseModel):
    """Model for running the processing pipeline."""
    max_applicants: Optional[int] = None
    stop_on_error: bool = False
    skip_processed: bool = True


def require_admin(auth_token: Optional[str] = Cookie(None)) -> dict:
    """Admin guard for admin endpoints."""
    from ..auth import verify_token_with_context
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token_data


def get_scholarship_config_path(scholarship_name: str) -> Path:
    """Get path to canonical config.yml for a scholarship."""
    return Path("data") / scholarship_name / "config.yml"


def load_scholarship_config(scholarship_name: str) -> Dict[str, Any]:
    """Load canonical scholarship config."""
    config_path = get_scholarship_config_path(scholarship_name)
    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Config file not found for scholarship {scholarship_name}: {config_path}",
        )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        logger.error(f"Error loading scholarship config {config_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load scholarship config")


def save_scholarship_config(scholarship_name: str, config: Dict[str, Any]) -> None:
    """Save canonical scholarship config."""
    config_path = get_scholarship_config_path(scholarship_name)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Error saving scholarship config {config_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save scholarship config")


@router.get("/{scholarship}/weights", operation_id="get_scholarship_weights")
async def get_weights(
    scholarship: str,
    token_data: dict = Depends(require_admin)
):
    """Get scoring weights for a scholarship.
    
    Returns the weights configuration from the scholarship's weights.json file.
    """
    import json
    
    try:
        # Load from weights.json
        weights_path = Path("data") / scholarship / "weights.json"
        if not weights_path.exists():
            raise HTTPException(status_code=404, detail=f"Weights file not found: {weights_path}")
        
        with open(weights_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        weights = data.get("weights", {})
        
        return {"weights": weights}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weights for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{scholarship}/weights", operation_id="update_scholarship_weights")
async def update_weights(
    scholarship: str,
    weights_update: WeightsUpdate,
    token_data: dict = Depends(require_admin)
):
    """Update scoring weights for a scholarship.
    
    Updates the weights in weights.json and triggers artifact regeneration.
    """
    import json
    
    try:
        # Load current weights
        weights_path = Path("data") / scholarship / "weights.json"
        if not weights_path.exists():
            raise HTTPException(status_code=404, detail=f"Weights file not found: {weights_path}")
        
        with open(weights_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Update weights
        data["weights"] = weights_update.weights
        
        # Recalculate total
        total = sum(w.get("weight", 0) for w in weights_update.weights.values())
        data["total_weight"] = round(total, 2)
        
        # Save updated weights
        with open(weights_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        # TODO: Trigger artifact regeneration
        logger.info(f"Updated weights for {scholarship}, artifacts should be regenerated")
        
        return {
            "detail": "Weights updated successfully",
            "weights": weights_update.weights
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating weights for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scholarship}/criteria/{agent}", operation_id="get_agent_criteria")
async def get_criteria(
    scholarship: str,
    agent: str,
    token_data: dict = Depends(require_admin)
):
    """Get evaluation criteria for a specific agent.
    
    Returns the criteria text from the agent's criteria text file.
    """
    try:
        # Path to agent criteria file (use .txt extension)
        criteria_path = Path("data") / scholarship / "criteria" / f"{agent}_criteria.txt"
        
        if not criteria_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Criteria file not found: {criteria_path}"
            )
        
        with open(criteria_path, "r", encoding="utf-8") as f:
            criteria_text = f.read()
        
        return {"criteria_text": criteria_text}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting criteria for {scholarship}/{agent}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{scholarship}/criteria/{agent}", operation_id="update_agent_criteria")
async def update_criteria(
    scholarship: str,
    agent: str,
    criteria_update: CriteriaUpdate,
    token_data: dict = Depends(require_admin)
):
    """Update evaluation criteria for a specific agent.
    
    Saves the criteria text to the agent's criteria text file and triggers artifact regeneration.
    """
    try:
        # Path to agent criteria file (use .txt extension)
        criteria_path = Path("data") / scholarship / "criteria" / f"{agent}_criteria.txt"
        criteria_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save criteria
        with open(criteria_path, "w", encoding="utf-8") as f:
            f.write(criteria_update.criteria_text)
        
        # TODO: Trigger artifact regeneration
        logger.info(f"Updated criteria for {scholarship}/{agent}, artifacts should be regenerated")
        
        return {"detail": "Criteria updated successfully"}
    except Exception as e:
        logger.error(f"Error updating criteria for {scholarship}/{agent}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scholarship}/criteria/{agent}/regenerate", operation_id="regenerate_agent_criteria")
async def regenerate_criteria(
    scholarship: str,
    agent: str,
    request: CriteriaRegenerateRequest,
    token_data: dict = Depends(require_admin)
):
    """Regenerate evaluation criteria using an LLM.
    
    Uses an LLM to propose new criteria based on the scholarship description and current criteria.
    """
    try:
        # Load current criteria
        criteria_path = Path("data") / scholarship / "criteria" / f"{agent}_criteria.md"
        current_criteria = ""
        if criteria_path.exists():
            with open(criteria_path, "r", encoding="utf-8") as f:
                current_criteria = f.read()
        
        # Load scholarship config for context
        config = load_scholarship_config(scholarship)
        scholarship_description = config.get("description", "")
        
        # TODO: Implement LLM-based criteria regeneration
        # For now, return a placeholder
        proposed_text = f"""# Proposed Criteria for {agent}

This is a placeholder for LLM-generated criteria.

## Current Context
- Scholarship: {scholarship}
- Agent: {agent}
- Description: {scholarship_description}

## Instructions
The LLM would analyze the scholarship requirements and propose updated criteria here.

Target Model: {request.target_model or 'default'}
"""
        
        logger.info(f"Generated proposal for {scholarship}/{agent} (placeholder)")
        
        return {
            "proposed_criteria_text": proposed_text,
            "detail": "Criteria proposal generated (placeholder implementation)"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating criteria for {scholarship}/{agent}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scholarship}/pipeline/run", operation_id="run_scholarship_pipeline")
async def run_pipeline(
    scholarship: str,
    request: PipelineRunRequest,
    token_data: dict = Depends(require_admin)
):
    """Trigger the scholarship processing pipeline.
    
    This is currently a stub that accepts the request but doesn't execute the full workflow.
    """
    try:
        logger.info(
            f"Pipeline run requested for {scholarship}: "
            f"max_applicants={request.max_applicants}, "
            f"stop_on_error={request.stop_on_error}, "
            f"skip_processed={request.skip_processed}"
        )
        
        # TODO: Implement actual pipeline execution
        # This would trigger the full workflow with the specified options
        
        return {
            "detail": f"Pipeline trigger accepted for {scholarship} (stub implementation)",
            "scholarship": scholarship,
            "options": {
                "max_applicants": request.max_applicants,
                "stop_on_error": request.stop_on_error,
                "skip_processed": request.skip_processed
            }
        }
    except Exception as e:
        logger.error(f"Error triggering pipeline for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Made with Bob