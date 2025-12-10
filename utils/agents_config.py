"""Agents configuration loader utility.

This module provides functions to load and validate agent configurations
from scholarship-specific agents.json files.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Optional


def load_agents_config(scholarship_folder: Path) -> dict:
    """Load agents configuration from scholarship folder.
    
    Args:
        scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
        
    Returns:
        Dictionary containing agents configuration.
        
    Raises:
        FileNotFoundError: If agents.json doesn't exist.
        
    Example:
        >>> config = load_agents_config(Path("data/Delaney_Wings"))
        >>> print(config['scholarship_name'])
        Delaney_Wings
    """
    logger = logging.getLogger()
    
    agents_file = scholarship_folder / "agents.json"
    
    if not agents_file.exists():
        raise FileNotFoundError(f"Agents config file not found: {agents_file}")
    
    try:
        with open(agents_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info(f"Loaded agents config from: {agents_file}")
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in agents config file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading agents config: {e}")
        raise


def get_agent_config(scholarship_folder: Path, agent_name: str) -> Optional[dict]:
    """Get configuration for a specific agent.
    
    Args:
        scholarship_folder: Path to scholarship folder.
        agent_name: Name of agent (e.g., "application", "recommendation").
        
    Returns:
        Agent configuration dictionary, or None if not found.
        
    Example:
        >>> config = get_agent_config(Path("data/Delaney_Wings"), "essay")
        >>> print(config['weight'])
        0.30
    """
    agents_config = load_agents_config(scholarship_folder)
    
    for agent in agents_config['agents']:
        if agent['name'] == agent_name:
            return agent
    
    return None


def get_enabled_agents(scholarship_folder: Path) -> list[dict]:
    """Get list of enabled agents.
    
    Args:
        scholarship_folder: Path to scholarship folder.
        
    Returns:
        List of enabled agent configurations.
        
    Example:
        >>> agents = get_enabled_agents(Path("data/Delaney_Wings"))
        >>> print(len(agents))
        5
    """
    agents_config = load_agents_config(scholarship_folder)
    return [agent for agent in agents_config['agents'] if agent.get('enabled', True)]


def get_scoring_agents(scholarship_folder: Path) -> list[dict]:
    """Get list of agents that contribute to scoring.
    
    Args:
        scholarship_folder: Path to scholarship folder.
        
    Returns:
        List of scoring agent configurations.
        
    Example:
        >>> agents = get_scoring_agents(Path("data/Delaney_Wings"))
        >>> print([a['name'] for a in agents])
        ['application', 'recommendation', 'academic', 'essay']
    """
    agents_config = load_agents_config(scholarship_folder)
    scoring_agent_names = agents_config.get('scoring_agents', [])
    
    return [
        agent for agent in agents_config['agents']
        if agent['name'] in scoring_agent_names
    ]


def validate_agents_config(scholarship_folder: Path) -> tuple[bool, list[str]]:
    """Validate agents configuration.
    
    Args:
        scholarship_folder: Path to scholarship folder.
        
    Returns:
        Tuple of (is_valid, list_of_errors).
        
    Example:
        >>> is_valid, errors = validate_agents_config(Path("data/Delaney_Wings"))
        >>> print(is_valid)
        True
    """
    errors = []
    
    try:
        config = load_agents_config(scholarship_folder)
    except Exception as e:
        return False, [f"Failed to load config: {str(e)}"]
    
    # Check required fields
    required_fields = ['scholarship_name', 'agents', 'scoring_agents']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Validate agents
    if 'agents' in config:
        agent_names = set()
        for i, agent in enumerate(config['agents']):
            # Check required agent fields
            required_agent_fields = ['name', 'display_name', 'description']
            for field in required_agent_fields:
                if field not in agent:
                    errors.append(f"Agent {i}: Missing required field '{field}'")
            
            # Check for duplicate names
            if 'name' in agent:
                if agent['name'] in agent_names:
                    errors.append(f"Duplicate agent name: {agent['name']}")
                agent_names.add(agent['name'])
        
        # Validate scoring agents references valid agents
        if 'scoring_agents' in config:
            for agent_name in config['scoring_agents']:
                if agent_name not in agent_names:
                    errors.append(f"Scoring agents references unknown agent: {agent_name}")
    
    return len(errors) == 0, errors


def print_agents_summary(scholarship_folder: Path) -> None:
    """Print a summary of agents configuration.
    
    Args:
        scholarship_folder: Path to scholarship folder.
        
    Example:
        >>> print_agents_summary(Path("data/Delaney_Wings"))
        Scholarship: Delaney_Wings
        Agents: 5
        ...
    """
    logger = logging.getLogger()
    
    config = load_agents_config(scholarship_folder)
    
    logger.info("="*60)
    logger.info(f"Agents Configuration: {config['scholarship_name']}")
    logger.info("="*60)
    logger.info(f"Description: {config['description']}")
    logger.info(f"Version: {config['version']}")
    logger.info(f"\nTotal Agents: {len(config['agents'])}")
    
    logger.info("\nScoring Agents:")
    for agent in get_scoring_agents(scholarship_folder):
        weight = agent.get('weight', 0)
        logger.info(f"  - {agent['display_name']}: {weight:.2f}")
    
    logger.info("\nAll Agents:")
    for agent in config['agents']:
        enabled = "✓" if agent.get('enabled', True) else "✗"
        required = "Required" if agent.get('required', False) else "Optional"
        logger.info(f"  {enabled} {agent['display_name']} ({required})")
        logger.info(f"     {agent['description']}")

# Made with Bob
