"""Tests for API criteria endpoints.

This module tests the criteria retrieval endpoints of the API.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-10
Version: 1.0.0
License: MIT
"""

import pytest


def test_list_criteria(test_client):
    """Test listing all available criteria."""
    response = test_client.get("/criteria")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "scholarship" in data
    assert "criteria_count" in data
    assert "criteria" in data
    
    assert data["scholarship"] == "Delaney_Wings"
    assert isinstance(data["criteria"], list)
    assert data["criteria_count"] > 0
    
    # Check that each criteria has required fields
    for criteria in data["criteria"]:
        assert "type" in criteria
        assert "name" in criteria
        assert "description" in criteria
        assert "filename" in criteria
        assert "url" in criteria


def test_get_application_criteria(test_client):
    """Test getting application criteria."""
    response = test_client.get("/criteria/application")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "scholarship" in data
    assert "criteria_type" in data
    assert "filename" in data
    assert "content" in data
    assert "line_count" in data
    
    assert data["criteria_type"] == "application"
    assert data["filename"] == "application_criteria.txt"
    assert len(data["content"]) > 0
    assert data["line_count"] > 0


def test_get_academic_criteria(test_client):
    """Test getting academic criteria."""
    response = test_client.get("/criteria/academic")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["criteria_type"] == "academic"
    assert data["filename"] == "academic_criteria.txt"
    assert "Academic" in data["content"]


def test_get_essay_criteria(test_client):
    """Test getting essay criteria."""
    response = test_client.get("/criteria/essay")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["criteria_type"] == "essay"
    assert data["filename"] == "essay_criteria.txt"


def test_get_recommendation_criteria(test_client):
    """Test getting recommendation criteria."""
    response = test_client.get("/criteria/recommendation")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["criteria_type"] == "recommendation"
    assert data["filename"] == "recommendation_criteria.txt"


def test_get_invalid_criteria_type(test_client):
    """Test getting criteria with invalid type."""
    response = test_client.get("/criteria/invalid_type")
    
    assert response.status_code == 400
    data = response.json()
    
    assert "detail" in data
    assert "Invalid criteria type" in data["detail"]


def test_criteria_content_structure(test_client):
    """Test that criteria content has expected structure."""
    response = test_client.get("/criteria/application")
    
    assert response.status_code == 200
    data = response.json()
    
    content = data["content"]
    
    # Check for common criteria elements
    assert len(content) > 100  # Should have substantial content
    assert isinstance(content, str)
    
    # Application criteria should mention scoring
    assert "SCORING" in content.upper() or "SCORE" in content.upper()


def test_all_criteria_types_available(test_client):
    """Test that all expected criteria types are available."""
    response = test_client.get("/criteria")
    
    assert response.status_code == 200
    data = response.json()
    
    criteria_types = [c["type"] for c in data["criteria"]]
    
    # Check for expected criteria types
    expected_types = ["application", "academic", "essay", "recommendation"]
    for expected_type in expected_types:
        assert expected_type in criteria_types, f"Missing {expected_type} criteria"


# Made with Bob