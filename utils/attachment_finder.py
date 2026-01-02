"""Config-driven attachment file finder.

This module provides a unified way to find input files for agents
based on the input_files configuration in agents.json.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-01-01
Version: 1.0.0
License: MIT
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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


def find_agent_input_files(
    attachments_dir: Path,
    input_files_config: list,
    wai_number: Optional[str] = None
) -> list[Path]:
    """Find input files for an agent based on config.
    
    Supports multiple matching strategies:
    - Index-based: {"index": 0} matches the Nth file (0-indexed)
    - Pattern-based: {"pattern": "*_recommendation_*"} uses glob
    - Legacy string: "Resume" (treated as documentation only, uses index if available)
    
    Args:
        attachments_dir: Path to attachments folder (e.g., outputs/scholarship/WAI/attachments)
        input_files_config: List of input file specifications from agents.json
        wai_number: Optional WAI number for pattern matching
    
    Returns:
        List of file paths matching the config, in order
    
    Example:
        >>> config = [{"index": 0}, {"index": 1}]
        >>> files = find_agent_input_files(Path("outputs/Scholarship/12345/attachments"), config)
        >>> print([f.name for f in files])
        ['12345_0.txt', '12345_1.txt']
    """
    if not attachments_dir.exists():
        logger.warning(f"Attachments directory not found: {attachments_dir}")
        return []
    
    # Get all text files, sorted by name (which includes index)
    all_files = sorted(attachments_dir.glob("*.txt"))
    
    if not all_files:
        logger.warning(f"No .txt files found in {attachments_dir}")
        return []
    
    result = []
    
    for spec in input_files_config:
        if isinstance(spec, dict):
            # Index-based matching
            if "index" in spec:
                idx = spec["index"]
                if 0 <= idx < len(all_files):
                    result.append(all_files[idx])
                    logger.debug(f"Found file at index {idx}: {all_files[idx].name}")
                else:
                    logger.warning(f"Index {idx} out of range (have {len(all_files)} files)")
            
            # Pattern-based matching
            elif "pattern" in spec:
                pattern = spec["pattern"]
                # Replace {wai} placeholder if present
                if wai_number:
                    pattern = pattern.replace("{wai}", wai_number)
                
                matched = list(attachments_dir.glob(pattern))
                if matched:
                    # Sort for consistency and take up to max if specified
                    matched = sorted(matched)
                    max_files = spec.get("max", len(matched))
                    result.extend(matched[:max_files])
                    logger.debug(f"Pattern '{pattern}' matched {len(matched)} files")
                else:
                    logger.warning(f"Pattern '{pattern}' matched no files")
        
        elif isinstance(spec, str):
            # Legacy string format - treat as documentation only
            # Try to extract index from patterns like "index: 3" or just log
            logger.debug(f"Legacy input_files format: '{spec}' (not matched)")
    
    return result


def find_input_files_for_agent(
    scholarship_folder: Path,
    agent_name: str,
    wai_number: str,
    output_base: Path = Path("outputs")
) -> list[Path]:
    """High-level function to find input files for an agent.
    
    Loads agent config and finds matching files in the WAI attachments folder.
    
    Args:
        scholarship_folder: Path to scholarship data folder (e.g., data/Delaney_Wings)
        agent_name: Name of the agent (e.g., "essay", "recommendation")
        wai_number: WAI application number
        output_base: Base output directory (default: "outputs")
    
    Returns:
        List of file paths for the agent to process
    
    Example:
        >>> files = find_input_files_for_agent(
        ...     Path("data/WAI-Harvard-June-2026"),
        ...     "essay",
        ...     "12345"
        ... )
    """
    # Load agent config
    agent_config = load_agent_config(scholarship_folder, agent_name)
    if not agent_config:
        return []
    
    input_files_config = agent_config.get("input_files", [])
    if not input_files_config:
        logger.warning(f"No input_files configured for agent '{agent_name}'")
        return []
    
    # Build attachments path
    scholarship_name = scholarship_folder.name
    attachments_dir = output_base / scholarship_name / wai_number / "attachments"
    
    return find_agent_input_files(attachments_dir, input_files_config, wai_number)


# Convenience functions for backward compatibility

def find_recommendation_files_from_config(
    scholarship_folder: Path,
    wai_number: str,
    output_base: Path = Path("outputs")
) -> list[Path]:
    """Find recommendation files using config-driven approach."""
    return find_input_files_for_agent(scholarship_folder, "recommendation", wai_number, output_base)


def find_essay_files_from_config(
    scholarship_folder: Path,
    wai_number: str,
    output_base: Path = Path("outputs")
) -> list[Path]:
    """Find essay files using config-driven approach."""
    return find_input_files_for_agent(scholarship_folder, "essay", wai_number, output_base)


def find_resume_files_from_config(
    scholarship_folder: Path,
    wai_number: str,
    output_base: Path = Path("outputs")
) -> list[Path]:
    """Find resume/academic files using config-driven approach."""
    # Try 'resume' first, fall back to 'academic'
    files = find_input_files_for_agent(scholarship_folder, "resume", wai_number, output_base)
    if not files:
        files = find_input_files_for_agent(scholarship_folder, "academic", wai_number, output_base)
    return files

