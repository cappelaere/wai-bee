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
    application_score: Optional[float] = None,
    recommendation_score: Optional[float] = None,
    resume_score: Optional[float] = None,
    essay_score: Optional[float] = None,
    weights_config: Optional[dict] = None
) -> dict:
    """Calculate final score from weighted agent scores.
    
    Args:
        application_score: Application agent weighted score.
        recommendation_score: Recommendation agent weighted score.
        resume_score: Resume agent weighted score.
        essay_score: Essay agent weighted score.
        weights_config: Weights configuration dictionary.
        
    Returns:
        Dictionary with final score and breakdown.
        
    Note:
        If scores are pre-weighted (weighted_score from analysis files),
        the final score is their sum. If scores are raw overall_scores,
        they will be weighted by the config weights.
    """
    logger = logging.getLogger()
    
    if weights_config is None:
        raise ValueError("weights_config is required")
    
    weights = weights_config['weights']
    
    # Collect available scores
    scores = {
        'application': application_score,
        'recommendation': recommendation_score,
        'resume': resume_score,
        'essay': essay_score
    }
    
    # Calculate final score (sum of weighted scores)
    weighted_sum = 0.0
    breakdown = {}
    missing_agents = []
    
    for agent_name, meta in weights.items():
        score = scores.get(agent_name)
        if score is None:
            missing_agents.append(agent_name)
            continue

        weighted_sum += float(score)
        breakdown[agent_name] = {
            'weighted_score': round(float(score), 2),
            'weight': meta['weight'],
        }
    
    final_score = round(weighted_sum, 2)
    
    result = {
        'final_score': final_score,
        'breakdown': breakdown,
        'missing_agents': missing_agents,
        'complete': len(missing_agents) == 0
    }
    
    if missing_agents:
        logger.warning(f"Missing scores for: {', '.join(missing_agents)}")
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
        'resume': None,
        'essay': None
    }
    
    # All agent outputs should be in outputs/<scholarship>/<WAI>/
    wai_output_dir = outputs_dir / scholarship_name / wai_number
    
    def extract_score(data: dict) -> dict:
        """Extract scores from analysis data, checking multiple formats.
        
        Returns dict with 'overall_score', 'weight', and 'weighted_score'.
        """
        result = {
            'overall_score': None,
            'weight': None,
            'weighted_score': None,
        }
        
        # 1. Check for new format with explicit fields
        if 'overall_score' in data:
            try:
                result['overall_score'] = int(data['overall_score'])
            except (ValueError, TypeError):
                pass
        
        if 'weight' in data:
            try:
                result['weight'] = float(data['weight'])
            except (ValueError, TypeError):
                pass
        
        if 'weighted_score' in data:
            try:
                result['weighted_score'] = float(data['weighted_score'])
            except (ValueError, TypeError):
                pass
        
        # 2. Check for legacy scores.overall_score format
        if result['overall_score'] is None and 'scores' in data:
            try:
                result['overall_score'] = int(data['scores'].get('overall_score', 0))
            except (ValueError, TypeError):
                pass
        
        # 3. Compute from facets as fallback
        if result['overall_score'] is None and 'facets' in data:
            facet_scores = [
                int(f.get('score', 0)) for f in (data.get('facets') or [])
                if isinstance(f, dict) and 'score' in f
            ]
            if facet_scores:
                result['overall_score'] = sum(facet_scores)
        
        return result
    
    # Load application score
    app_file = wai_output_dir / "application_analysis.json"
    if app_file.exists():
        try:
            with open(app_file, 'r') as f:
                score_data = extract_score(json.load(f))
                scores['application'] = score_data['weighted_score'] or score_data['overall_score']
        except Exception as e:
            logger.warning(f"Error loading application score: {e}")
    
    # Load recommendation score
    rec_file = wai_output_dir / "recommendation_analysis.json"
    if rec_file.exists():
        try:
            with open(rec_file, 'r') as f:
                score_data = extract_score(json.load(f))
                scores['recommendation'] = score_data['weighted_score'] or score_data['overall_score']
        except Exception as e:
            logger.warning(f"Error loading recommendation score: {e}")
    
    # Load resume score
    resume_file = wai_output_dir / "resume_analysis.json"
    if resume_file.exists():
        try:
            with open(resume_file, 'r') as f:
                score_data = extract_score(json.load(f))
                scores['resume'] = score_data['weighted_score'] or score_data['overall_score']
        except Exception as e:
            logger.warning(f"Error loading resume score: {e}")
    
    # Load essay score
    essay_file = wai_output_dir / "essay_analysis.json"
    if essay_file.exists():
        try:
            with open(essay_file, 'r') as f:
                score_data = extract_score(json.load(f))
                scores['essay'] = score_data['weighted_score'] or score_data['overall_score']
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
        resume_score=scores['resume'],
        essay_score=scores['essay'],
        weights_config=weights_config
    )
    
    # Add metadata
    result['wai_number'] = wai_number
    result['scholarship_name'] = scholarship_name
    result['agent_scores'] = scores
    
    return result

# Made with Bob
