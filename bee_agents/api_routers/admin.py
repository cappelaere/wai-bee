"""Admin endpoints for scholarship configuration management.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from ..api_utils import get_scholarship_config_path, load_scholarship_config

router = APIRouter(tags=["Admin"], prefix="/admin")
logger = logging.getLogger(__name__)


def require_admin(request: Request) -> None:
    """Placeholder admin guard for future integration.

    Currently assumes that access to /admin endpoints is restricted by
    deployment (e.g., API gateway, auth middleware).
    """
    return


@router.get("/{scholarship}/weights", operation_id="get_weights")
async def get_scholarship_weights(
    scholarship: str,
    _: None = Depends(require_admin),
):
    """Get current scoring weights for a scholarship from canonical config."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    scoring_cfg = config.get("scoring", {})
    scoring_agents = scoring_cfg.get("scoring_agents", [])

    weights = {}
    total = 0.0
    for name, agent in agents_cfg.items():
        weight = agent.get("weight")
        if weight is not None:
            weights[name] = {
                "weight": weight,
                "description": agent.get("description", ""),
                "enabled": agent.get("enabled", True),
                "required": agent.get("required", False),
            }
            total += weight

    return {
        "scholarship": scholarship,
        "weights": weights,
        "total_weight": round(total, 4),
        "scoring_agents": scoring_agents,
    }


@router.put("/{scholarship}/weights", operation_id="update_weights")
async def update_scholarship_weights(
    scholarship: str,
    payload: Dict[str, Any],
    _: None = Depends(require_admin),
):
    """Update scoring weights in canonical config and regenerate artifacts."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})

    new_weights = payload.get("weights", {})
    if not isinstance(new_weights, dict):
        raise HTTPException(status_code=400, detail="weights must be an object")

    # Update weights in config
    for agent_name, new_weight in new_weights.items():
        if agent_name not in agents_cfg:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")
        if not isinstance(new_weight, (int, float)):
            raise HTTPException(status_code=400, detail=f"Invalid weight for {agent_name}")
        agents_cfg[agent_name]["weight"] = float(new_weight)

    # Persist back to config.yml with simple backup
    config_path = get_scholarship_config_path(scholarship)
    backup_path = config_path.with_suffix(".backup")
    try:
        import shutil
        import yaml

        if config_path.exists():
            shutil.copy2(config_path, backup_path)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Failed to write updated weights for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save updated weights")

    # Regenerate artifacts (criteria/*.txt, etc.)
    try:
        from scripts.generate_scholarship_artifacts import main as generate_main

        root = Path(__file__).resolve().parents[2]
        generate_main([str(root / "scripts/generate_scholarship_artifacts.py"), scholarship])
    except Exception as e:
        logger.error(f"Failed to regenerate artifacts for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Weights saved but artifact regeneration failed")

    return {"status": "ok", "updated_agents": list(new_weights.keys())}


@router.get("/{scholarship}/criteria/{agent_name}", operation_id="get_criteria")
async def get_agent_criteria(
    scholarship: str,
    agent_name: str,
    _: None = Depends(require_admin),
):
    """Get current criteria text for an agent."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    criteria_text = config.get("criteria_text", {})

    if agent_name not in agents_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    agent_cfg = agents_cfg[agent_name]
    crit_ref = agent_cfg.get("criteria_ref")
    if not crit_ref:
        raise HTTPException(status_code=400, detail=f"Agent {agent_name} does not use criteria_ref")

    current_text = criteria_text.get(crit_ref, "")
    return {
        "scholarship": scholarship,
        "agent": agent_name,
        "criteria_ref": crit_ref,
        "criteria_text": current_text,
    }


@router.put("/{scholarship}/criteria/{agent_name}", operation_id="update_criteria")
async def update_agent_criteria(
    scholarship: str,
    agent_name: str,
    payload: Dict[str, Any],
    _: None = Depends(require_admin),
):
    """Update criteria text for an agent and regenerate artifacts."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    criteria_text = config.get("criteria_text", {})

    if agent_name not in agents_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    agent_cfg = agents_cfg[agent_name]
    crit_ref = agent_cfg.get("criteria_ref")
    if not crit_ref:
        raise HTTPException(status_code=400, detail=f"Agent {agent_name} does not use criteria_ref")

    new_text = payload.get("criteria_text")
    if not isinstance(new_text, str):
        raise HTTPException(status_code=400, detail="criteria_text must be a string")

    criteria_text[crit_ref] = new_text
    config["criteria_text"] = criteria_text

    # Persist back to config.yml with simple backup
    config_path = get_scholarship_config_path(scholarship)
    backup_path = config_path.with_suffix(".backup")
    try:
        import shutil
        import yaml

        if config_path.exists():
            shutil.copy2(config_path, backup_path)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Failed to write updated criteria for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save updated criteria")

    # Regenerate artifacts (criteria/*.txt, etc.)
    try:
        from scripts.generate_scholarship_artifacts import main as generate_main

        root = Path(__file__).resolve().parents[2]
        generate_main([str(root / "scripts/generate_scholarship_artifacts.py"), scholarship])
    except Exception as e:
        logger.error(f"Failed to regenerate artifacts for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Criteria saved but artifact regeneration failed")

    return {"status": "ok", "agent": agent_name}


@router.post("/{scholarship}/criteria/{agent_name}/regenerate", operation_id="regen_criteria")
async def regenerate_agent_criteria_with_llm(
    scholarship: str,
    agent_name: str,
    payload: Dict[str, Any],
    _: None = Depends(require_admin),
):
    """Generate a new criteria draft for an agent using an LLM.

    This endpoint does NOT persist changes automatically. It returns a
    proposed `criteria_text` that an admin can review and then apply via
    the standard PUT /admin/{scholarship}/criteria/{agent_name} endpoint.
    """
    from beeai_framework.backend.chat import ChatModel  # type: ignore

    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    criteria_text = config.get("criteria_text", {})

    if agent_name not in agents_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    agent_cfg = agents_cfg[agent_name]
    crit_ref = agent_cfg.get("criteria_ref")
    if not crit_ref:
        raise HTTPException(status_code=400, detail=f"Agent {agent_name} does not use criteria_ref")

    current_text = criteria_text.get(crit_ref, "")
    base_description = payload.get("base_description") or agent_cfg.get("description", "")
    target_model = payload.get("target_model") or os.getenv("PRIMARY_MODEL", "ollama:llama3.2:1b")

    system_prompt = (
        "You are an expert in designing scoring rubrics for scholarship application agents.\n"
        "Generate clear, structured evaluation criteria text suitable to be used as a prompt\n"
        "for an LLM that will score this agent. The output should be plain text with headings\n"
        "and bullet points, not JSON. Do not include instructions about JSON schemas.\n"
    )

    user_prompt_parts = [
        f"Scholarship ID: {scholarship}",
        f"Agent name: {agent_name}",
        f"Agent description: {base_description}",
        f"Target model identifier: {target_model}",
    ]
    if current_text:
        user_prompt_parts.append(
            "Current criteria text (improve and refine, but keep intent compatible):\n"
            f"{current_text}"
        )
    else:
        user_prompt_parts.append("No existing criteria text; create a new rubric from scratch.")

    user_prompt = "\n\n".join(user_prompt_parts)

    try:
        chat_model = ChatModel.from_name(target_model)
        from beeai_framework.backend.message import UserMessage  # type: ignore

        messages = [
            UserMessage(system_prompt),
            UserMessage(user_prompt),
        ]
        # Run synchronously via asyncio wrapper
        import asyncio

        async def _run():
            result = await chat_model.run(messages)
            return result.last_message.text if result and result.last_message else ""

        new_text = asyncio.run(_run())
    except Exception as e:
        logger.error(f"Failed to regenerate criteria with LLM for {scholarship}/{agent_name}: {e}")
        raise HTTPException(status_code=500, detail="LLM criteria generation failed")

    if not new_text or len(new_text) < 100:
        raise HTTPException(status_code=500, detail="Generated criteria text is too short or empty")

    return {
        "scholarship": scholarship,
        "agent": agent_name,
        "criteria_ref": crit_ref,
        "current_criteria_text": current_text,
        "proposed_criteria_text": new_text,
    }

# Made with Bob
