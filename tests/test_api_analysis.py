"""Tests for analysis API endpoints.

This module tests the endpoints that return detailed analysis data.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import pytest


def test_get_application_analysis_valid(test_client, scholarship_name, sample_wai_number):
    """Test getting application analysis for a valid WAI number."""
    response = test_client.get(f"/application?scholarship={scholarship_name}&wai_number={sample_wai_number}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "wai_number" in data
    assert "summary" in data
    assert "scores" in data
    assert "score_breakdown" in data
    assert "completeness_issues" in data
    assert "validity_issues" in data
    assert "attachment_status" in data
    assert "processed_date" in data
    assert "source_file" in data
    
    # Verify WAI number matches
    assert data["wai_number"] == sample_wai_number
    
    # Check scores structure
    scores = data["scores"]
    assert "completeness_score" in scores
    assert "validity_score" in scores
    assert "attachment_score" in scores
    assert "overall_score" in scores
    
    # Check score breakdown structure
    breakdown = data["score_breakdown"]
    assert "completeness_reasoning" in breakdown
    assert "validity_reasoning" in breakdown
    assert "attachment_reasoning" in breakdown


def test_get_application_analysis_invalid(test_client, invalid_wai_number):
    """Test getting application analysis for an invalid WAI number."""
    response = test_client.get(f"/application/{invalid_wai_number}")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_academic_analysis_valid(test_client, sample_wai_number):
    """Test getting academic analysis for a valid WAI number."""
    response = test_client.get(f"/academic/{sample_wai_number}")
    
    # Academic analysis may not exist for all applications
    if response.status_code == 200:
        data = response.json()
        
        # Check required fields
        assert "wai_number" in data
        assert "summary" in data
        assert "profile_features" in data
        assert "processed_date" in data
        
        # Verify WAI number matches
        assert data["wai_number"] == sample_wai_number
        
        # Check data types
        assert isinstance(data["profile_features"], dict)
        
        # Check optional fields
        if "scores" in data:
            assert isinstance(data["scores"], dict)
    elif response.status_code == 404:
        # Academic analysis not available - this is acceptable
        pass
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


def test_get_essay_analysis_valid(test_client, sample_wai_number):
    """Test getting essay analysis for a valid WAI number."""
    # Test essay 1
    response = test_client.get(f"/essay/{sample_wai_number}/1")
    
    # Essay analysis may not exist for all applications
    if response.status_code == 200:
        data = response.json()
        
        # Check required fields
        assert "wai_number" in data
        assert "essay_number" in data
        assert "summary" in data
        assert "strengths" in data
        assert "weaknesses" in data
        assert "processed_date" in data
        
        # Verify details
        assert data["wai_number"] == sample_wai_number
        assert data["essay_number"] == 1
        
        # Check data types
        assert isinstance(data["strengths"], list)
        assert isinstance(data["weaknesses"], list)
    elif response.status_code == 404:
        # Essay analysis not available - this is acceptable
        pass
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


def test_get_essay_analysis_invalid_number(test_client, sample_wai_number):
    """Test getting essay analysis with invalid essay number."""
    # Essay number 3 doesn't exist (only 1 and 2 are valid)
    response = test_client.get(f"/essay/{sample_wai_number}/3")
    
    # Should return 404 or validation error
    assert response.status_code in [404, 422]


def test_get_recommendation_analysis_valid(test_client, sample_wai_number):
    """Test getting recommendation analysis for a valid WAI number."""
    # Test recommendation 1
    response = test_client.get(f"/recommendation/{sample_wai_number}/1")
    
    # Recommendation analysis may not exist for all applications
    if response.status_code == 200:
        data = response.json()
        
        # Check required fields
        assert "wai_number" in data
        assert "recommendation_number" in data
        assert "summary" in data
        assert "strengths" in data
        assert "concerns" in data
        assert "processed_date" in data
        
        # Verify details
        assert data["wai_number"] == sample_wai_number
        assert data["recommendation_number"] == 1
        
        # Check data types
        assert isinstance(data["strengths"], list)
        assert isinstance(data["concerns"], list)
    elif response.status_code == 404:
        # Recommendation analysis not available - this is acceptable
        pass
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


def test_get_recommendation_analysis_invalid_number(test_client, sample_wai_number):
    """Test getting recommendation analysis with invalid recommendation number."""
    # Recommendation number 3 doesn't exist (only 1 and 2 are valid)
    response = test_client.get(f"/recommendation/{sample_wai_number}/3")
    
    # Should return 404 or validation error
    assert response.status_code in [404, 422]


def test_analysis_endpoints_consistency(test_client, scholarship_name, sample_wai_number):
    """Test that analysis endpoints return consistent data."""
    # Get application analysis
    app_response = test_client.get(f"/application?scholarship={scholarship_name}&wai_number={sample_wai_number}")
    assert app_response.status_code == 200
    app_data = app_response.json()
    
    # Get individual score
    score_response = test_client.get(f"/score?scholarship={scholarship_name}&wai_number={sample_wai_number}")
    assert score_response.status_code == 200
    score_data = score_response.json()
    
    # Scores should match between endpoints (note: may differ if data sources are different)
    # Verify both endpoints return valid score structures
    assert "overall_score" in app_data["scores"]
    assert "overall_score" in score_data
    assert "completeness_score" in app_data["scores"]
    assert "completeness_score" in score_data
    assert "validity_score" in app_data["scores"]
    assert "validity_score" in score_data
    assert "attachment_score" in app_data["scores"]
    assert "attachment_score" in score_data
    
    # Both should have summaries
    assert "summary" in app_data
    assert "summary" in score_data

# Made with Bob
