"""Tests for score-related API endpoints.

This module tests the endpoints that return application scores.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import pytest


def test_get_top_scores_default(test_client, scholarship_name):
    """Test getting top scores with default limit."""
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "scholarship" in data
    assert "total_applications" in data
    assert "top_scores" in data
    
    assert data["scholarship"] == scholarship_name
    assert isinstance(data["top_scores"], list)
    assert len(data["top_scores"]) <= 10  # Default limit


def test_get_top_scores_custom_limit(test_client, scholarship_name):
    """Test getting top scores with custom limit."""
    limit = 5
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}&limit={limit}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["top_scores"]) <= limit


def test_get_top_scores_validates_limit(test_client, scholarship_name):
    """Test that limit parameter is validated."""
    # Test limit too high
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}&limit=200")
    assert response.status_code == 422  # Validation error
    
    # Test limit too low
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}&limit=0")
    assert response.status_code == 422  # Validation error


def test_top_scores_structure(test_client, scholarship_name):
    """Test that top scores have correct structure."""
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}&limit=1")
    
    assert response.status_code == 200
    data = response.json()
    
    if data["top_scores"]:
        score = data["top_scores"][0]
        
        # Check required fields
        assert "wai_number" in score
        assert "overall_score" in score
        assert "completeness_score" in score
        assert "validity_score" in score
        assert "attachment_score" in score
        assert "summary" in score
        
        # Check applicant information fields (optional)
        assert "name" in score
        assert "city" in score
        assert "state" in score
        assert "country" in score
        
        # Check score ranges (scores can be > 100 in current scoring system)
        assert score["overall_score"] >= 0
        assert score["completeness_score"] >= 0
        assert score["validity_score"] >= 0
        assert score["attachment_score"] >= 0


def test_get_individual_score_valid(test_client, scholarship_name, sample_wai_number):
    """Test getting score for a valid WAI number."""
    response = test_client.get(f"/score?scholarship={scholarship_name}&wai_number={sample_wai_number}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["wai_number"] == sample_wai_number
    assert "overall_score" in data
    assert "completeness_score" in data
    assert "validity_score" in data
    assert "attachment_score" in data
    assert "summary" in data
    
    # Check applicant information fields
    assert "name" in data
    assert "city" in data
    assert "state" in data
    assert "country" in data
    
    # Verify score ranges (scores can be > 100 in current scoring system)
    assert data["overall_score"] >= 0
    assert data["completeness_score"] >= 0
    assert data["validity_score"] >= 0
    assert data["attachment_score"] >= 0


def test_get_individual_score_invalid(test_client, scholarship_name, invalid_wai_number):
    """Test getting score for an invalid WAI number."""
    response = test_client.get(f"/score?scholarship={scholarship_name}&wai_number={invalid_wai_number}")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_top_scores_sorted_descending(test_client, scholarship_name):
    """Test that top scores are sorted in descending order."""
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    scores = [s["overall_score"] for s in data["top_scores"]]
    
    # Check that scores are in descending order
    assert scores == sorted(scores, reverse=True)

# Made with Bob
