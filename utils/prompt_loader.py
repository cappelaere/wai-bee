"""Prompt loader utility for loading agent prompts from agents.json config.

This module provides functions to load analysis and repair prompts
for agents based on the agents.json configuration.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-01-01
Version: 1.0.0
License: MIT
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_SCHEMA_TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)_SCHEMA\}\}")


def _inject_schema_placeholders(scholarship_folder: Path, prompt_text: str) -> str:
    """Replace {{<AGENT>_SCHEMA}} tokens in prompt text with the actual schema JSON.

    Example tokens:
      - {{RESUME_SCHEMA}}
      - {{ESSAY_SCHEMA}}

    The token prefix is mapped to a lower-case agent name, e.g. RESUME -> resume.
    """
    matches = list(_SCHEMA_TOKEN_RE.finditer(prompt_text))
    if not matches:
        return prompt_text

    out = prompt_text
    for m in matches:
        agent_token = m.group(1)
        agent_name = agent_token.lower()

        schema_path = load_schema_path(scholarship_folder, agent_name)
        if not schema_path:
            raise ValueError(
                f"Prompt contains schema token '{{{{{agent_token}_SCHEMA}}}}' but "
                f"no schema path is configured for agent '{agent_name}' in agents.json"
            )
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Prompt contains schema token '{{{{{agent_token}_SCHEMA}}}}' but "
                f"schema file not found: {schema_path}"
            )

        try:
            schema_obj = json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse schema JSON at {schema_path}: {e}") from e

        schema_json = json.dumps(schema_obj, indent=2, ensure_ascii=False)
        out = out.replace(f"{{{{{agent_token}_SCHEMA}}}}", schema_json)

    return out


def load_agent_config(scholarship_folder: Path, agent_name: str) -> Optional[dict]:
    """Load configuration for a specific agent from agents.json.
    
    Args:
        scholarship_folder: Path to scholarship data folder
        agent_name: Name of the agent (e.g., "essay", "recommendation")
    
    Returns:
        Agent configuration dict or None if not found
    """
    agents_file = scholarship_folder / "agents.json"
    
    if not agents_file.exists():
        logger.warning(f"agents.json not found: {agents_file}")
        return None
    
    try:
        with open(agents_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for agent in config.get('agents', []):
            if agent.get('name') == agent_name:
                return agent
        
        logger.warning(f"Agent '{agent_name}' not found in agents.json")
        return None
        
    except Exception as e:
        logger.error(f"Error loading agents.json: {e}")
        return None


def load_analysis_prompt(scholarship_folder: Path, agent_name: str) -> Optional[str]:
    """Load the analysis prompt for an agent.
    
    Args:
        scholarship_folder: Path to scholarship data folder
        agent_name: Name of the agent (e.g., "essay", "recommendation")
    
    Returns:
        Analysis prompt text or None if not found
    
    Example:
        >>> prompt = load_analysis_prompt(Path("data/WAI-Harvard-June-2026"), "essay")
        >>> print(prompt[:50])
        "# Analysis prompt for essay..."
    """
    agent_config = load_agent_config(scholarship_folder, agent_name)
    if not agent_config:
        return None
    
    prompt_path = agent_config.get('analysis_prompt')
    if not prompt_path:
        logger.warning(f"No analysis_prompt defined for agent '{agent_name}'")
        return None
    
    # Resolve relative path
    full_path = scholarship_folder / prompt_path
    
    if not full_path.exists():
        logger.warning(f"Analysis prompt file not found: {full_path}")
        return None
    
    try:
        text = full_path.read_text(encoding='utf-8')
        return _inject_schema_placeholders(scholarship_folder, text)
    except Exception as e:
        logger.error(f"Error reading analysis prompt: {e}")
        return None


def load_repair_prompt(scholarship_folder: Path, agent_name: str) -> Optional[str]:
    """Load the repair prompt for an agent.
    
    Args:
        scholarship_folder: Path to scholarship data folder
        agent_name: Name of the agent (e.g., "essay", "recommendation")
    
    Returns:
        Repair prompt text or None if not found
    """
    agent_config = load_agent_config(scholarship_folder, agent_name)
    if not agent_config:
        return None
    
    prompt_path = agent_config.get('repair_prompt')
    if not prompt_path:
        logger.warning(f"No repair_prompt defined for agent '{agent_name}'")
        return None
    
    # Resolve relative path
    full_path = scholarship_folder / prompt_path
    
    if not full_path.exists():
        logger.warning(f"Repair prompt file not found: {full_path}")
        return None
    
    try:
        text = full_path.read_text(encoding='utf-8')
        return _inject_schema_placeholders(scholarship_folder, text)
    except Exception as e:
        logger.error(f"Error reading repair prompt: {e}")
        return None


def load_prompts(scholarship_folder: Path, agent_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Load both analysis and repair prompts for an agent.
    
    Args:
        scholarship_folder: Path to scholarship data folder
        agent_name: Name of the agent (e.g., "essay", "recommendation")
    
    Returns:
        Tuple of (analysis_prompt, repair_prompt), either can be None
    
    Example:
        >>> analysis, repair = load_prompts(Path("data/WAI-Harvard-June-2026"), "essay")
    """
    return (
        load_analysis_prompt(scholarship_folder, agent_name),
        load_repair_prompt(scholarship_folder, agent_name)
    )


def load_schema_path(scholarship_folder: Path, agent_name: str) -> Optional[Path]:
    """Get the full path to an agent's output schema.
    
    Args:
        scholarship_folder: Path to scholarship data folder
        agent_name: Name of the agent
    
    Returns:
        Full path to schema file or None if not found
    """
    agent_config = load_agent_config(scholarship_folder, agent_name)
    if not agent_config:
        return None
    
    schema_path = agent_config.get('schema')
    if not schema_path:
        return None
    
    return scholarship_folder / schema_path


def get_agent_output_config(scholarship_folder: Path, agent_name: str) -> dict:
    """Get output configuration for an agent.
    
    Args:
        scholarship_folder: Path to scholarship data folder
        agent_name: Name of the agent
    
    Returns:
        Dict with output_directory and output_file, or empty dict
    """
    agent_config = load_agent_config(scholarship_folder, agent_name)
    if not agent_config:
        return {}
    
    return {
        'output_directory': agent_config.get('output_directory', f'outputs/{agent_name}'),
        'output_file': agent_config.get('output_file', f'{{id}}_{agent_name}_analysis.json')
    }

