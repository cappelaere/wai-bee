"""Score calculator utility for weighted agent scoring.

This module provides functions to load scholarship weights and calculate
final weighted scores from multiple agent outputs.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Optional


def load_weights(scholarship_folder: Path) -> dict:
    """Load scoring weights from agents.json in scholarship folder.
    
    Args:
        scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
        
    Returns:
        Dictionary containing weights configuration.
        
    Raises:
        FileNotFoundError: If agents.json doesn't exist.
        ValueError: If weights don't sum to 1.0.
        
    Example:
        >>> weights = load_weights(Path("data/Delaney_Wings"))
        >>> print(weights['weights']['essay']['weight'])
        0.30
    """
    logger = logging.getLogger()
    
    agents_file = scholarship_folder / "agents.json"
    
    if not agents_file.exists():
        raise FileNotFoundError(f"agents.json not found in {scholarship_folder}")
    
    try:
        with open(agents_file, 'r', encoding='utf-8') as f:
            agents_config = json.load(f)
        
        # Extract weights from agents
        weights = {}
        for agent in agents_config['agents']:
            if agent.get('weight') is not None:
                weights[agent['name']] = {
                    'weight': agent['weight'],
                    'description': agent['description']
                }
        
        # Validate weights sum to 1.0
        total = sum(w['weight'] for w in weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        weights_config = {
            'scholarship_name': agents_config['scholarship_name'],
            'description': "Weights from agents.json",
            'weights': weights,
            'total_weight': total
        }
        
        logger.info(f"Loaded weights from: {agents_file}")
        return weights_config
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in agents file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading weights from agents file: {e}")
        raise


def calculate_final_score(
    application_score: Optional[int] = None,
    recommendation_score: Optional[int] = None,
    academic_score: Optional[int] = None,
    essay_score: Optional[int] = None,
    weights_config: Optional[dict] = None
) -> dict:
    """Calculate weighted final score from agent scores.
    
    Args:
        application_score: Application agent overall score (0-100).
        recommendation_score: Recommendation agent overall score (0-100).
        academic_score: Academic agent overall score (0-100).
        essay_score: Essay agent overall score (0-100).
        weights_config: Weights configuration dictionary.
        
    Returns:
        Dictionary with final score and breakdown.
        
    Example:
        >>> weights = load_weights(Path("data/Delaney_Wings"))
        >>> result = calculate_final_score(
        ...     application_score=85,
        ...     recommendation_score=90,
        ...     academic_score=88,
        ...     essay_score=92,
        ...     weights_config=weights
        ... )
        >>> print(result['final_score'])
        89.1
    """
    logger = logging.getLogger()
    
    if weights_config is None:
        raise ValueError("weights_config is required")
    
    weights = weights_config['weights']
    
    # Collect available scores
    scores = {
        'application': application_score,
        'recommendation': recommendation_score,
        'academic': academic_score,
        'essay': essay_score
    }
    
    # Calculate weighted score
    weighted_sum = 0.0
    total_weight = 0.0
    breakdown = {}
    missing_agents = []
    
    for agent_name, score in scores.items():
        if score is not None:
            weight = weights[agent_name]['weight']
            contribution = score * weight
            weighted_sum += contribution
            total_weight += weight
            breakdown[agent_name] = {
                'score': score,
                'weight': weight,
                'contribution': round(contribution, 2)
            }
        else:
            missing_agents.append(agent_name)
    
    # Calculate final score
    if total_weight > 0:
        final_score = round(weighted_sum / total_weight * (1.0 / total_weight), 2)
    else:
        final_score = 0.0
    
    result = {
        'final_score': round(weighted_sum, 2),
        'breakdown': breakdown,
        'total_weight_used': round(total_weight, 2),
        'missing_agents': missing_agents,
        'complete': len(missing_agents) == 0
    }
    
    if missing_agents:
        logger.warning(f"Missing scores for: {', '.join(missing_agents)}")
        logger.info(f"Final score calculated using {total_weight:.2f} of total weight")
    else:
        logger.info(f"Final score: {result['final_score']:.2f} (all agents complete)")
    
    return result


def load_agent_scores(
    outputs_dir: Path,
    scholarship_name: str,
    wai_number: str
) -> dict:
    """Load all agent scores for a WAI application.
    
    Args:
        outputs_dir: Base outputs directory.
        scholarship_name: Name of scholarship.
        wai_number: WAI application number.
        
    Returns:
        Dictionary with scores from each agent.
        
    Example:
        >>> scores = load_agent_scores(
        ...     Path("outputs"),
        ...     "Delaney_Wings",
        ...     "77747"
        ... )
        >>> print(scores['essay'])
        85
    """
    logger = logging.getLogger()
    
    scores = {
        'application': None,
        'recommendation': None,
        'academic': None,
        'essay': None
    }
    
    # All agent outputs should be in outputs/<scholarship>/<WAI>/
    wai_output_dir = outputs_dir / scholarship_name / wai_number
    
    # Load application score from analysis file
    app_analysis_file = wai_output_dir / "application_analysis.json"
    if app_analysis_file.exists():
        try:
            with open(app_analysis_file, 'r') as f:
                data = json.load(f)
                if 'scores' in data:
                    scores['application'] = data.get('scores', {}).get('overall_score')
                elif 'facets' in data:
                    facet_scores = [
                        int(f.get('score', 0)) for f in (data.get('facets') or [])
                        if isinstance(f, dict)
                    ]
                    if facet_scores:
                        scores['application'] = round(sum(facet_scores) / len(facet_scores), 2)
        except Exception as e:
            logger.warning(f"Error loading application score: {e}")
    
    # Load recommendation score
    rec_file = wai_output_dir / "recommendation_analysis.json"
    if rec_file.exists():
        try:
            with open(rec_file, 'r') as f:
                data = json.load(f)
                scores['recommendation'] = data.get('scores', {}).get('overall_score')
        except Exception as e:
            logger.warning(f"Error loading recommendation score: {e}")
    
    # Load academic score
    acad_file = wai_output_dir / "academic_analysis.json"
    if acad_file.exists():
        try:
            with open(acad_file, 'r') as f:
                data = json.load(f)
                scores['academic'] = data.get('scores', {}).get('overall_score')
        except Exception as e:
            logger.warning(f"Error loading academic score: {e}")
    
    # Load essay score
    essay_file = wai_output_dir / "essay_analysis.json"
    if essay_file.exists():
        try:
            with open(essay_file, 'r') as f:
                data = json.load(f)
                scores['essay'] = data.get('scores', {}).get('overall_score')
        except Exception as e:
            logger.warning(f"Error loading essay score: {e}")
    
    return scores


def calculate_wai_final_score(
    scholarship_folder: Path,
    outputs_dir: Path,
    scholarship_name: str,
    wai_number: str
) -> dict:
    """Calculate final weighted score for a WAI application.
    
    Loads weights, loads all agent scores, and calculates final score.
    
    Args:
        scholarship_folder: Path to scholarship folder with agents.json.
        outputs_dir: Base outputs directory.
        scholarship_name: Name of scholarship.
        wai_number: WAI application number.
        
    Returns:
        Dictionary with final score and complete breakdown.
        
    Example:
        >>> result = calculate_wai_final_score(
        ...     Path("data/Delaney_Wings"),
        ...     Path("outputs"),
        ...     "Delaney_Wings",
        ...     "77747"
        ... )
        >>> print(f"Final score: {result['final_score']}")
        Final score: 89.1
    """
    # Load weights
    weights_config = load_weights(scholarship_folder)
    
    # Load agent scores
    scores = load_agent_scores(outputs_dir, scholarship_name, wai_number)
    
    # Calculate final score
    result = calculate_final_score(
        application_score=scores['application'],
        recommendation_score=scores['recommendation'],
        academic_score=scores['academic'],
        essay_score=scores['essay'],
        weights_config=weights_config
    )
    
    # Add metadata
    result['wai_number'] = wai_number
    result['scholarship_name'] = scholarship_name
    result['agent_scores'] = scores
    
    return result

# Made with Bob
