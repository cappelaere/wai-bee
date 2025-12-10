"""Tests for statistics API endpoint.

This module tests the statistics endpoint that provides aggregated data.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import pytest


def test_get_statistics(test_client):
    """Test getting statistics for all applications."""
    response = test_client.get("/statistics")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "scholarship" in data
    assert "total_applications" in data
    assert "average_score" in data
    assert "median_score" in data
    assert "min_score" in data
    assert "max_score" in data
    assert "score_distribution" in data
    
    # Verify scholarship name
    assert data["scholarship"] == "Delaney_Wings"
    
    # Verify data types
    assert isinstance(data["total_applications"], int)
    assert isinstance(data["average_score"], (int, float))
    assert isinstance(data["median_score"], (int, float))
    assert isinstance(data["min_score"], int)
    assert isinstance(data["max_score"], int)
    assert isinstance(data["score_distribution"], dict)


def test_statistics_score_ranges(test_client):
    """Test that statistics scores are within valid ranges."""
    response = test_client.get("/statistics")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check score ranges
    assert 0 <= data["average_score"] <= 100
    assert 0 <= data["median_score"] <= 100
    assert 0 <= data["min_score"] <= 100
    assert 0 <= data["max_score"] <= 100
    
    # Min should be <= median <= max
    assert data["min_score"] <= data["median_score"] <= data["max_score"]


def test_statistics_distribution_structure(test_client):
    """Test that score distribution has correct structure."""
    response = test_client.get("/statistics")
    
    assert response.status_code == 200
    data = response.json()
    
    distribution = data["score_distribution"]
    
    # Check expected ranges
    expected_ranges = ["90-100", "80-89", "70-79", "60-69", "50-59", "0-49"]
    for range_name in expected_ranges:
        assert range_name in distribution
        assert isinstance(distribution[range_name], int)
        assert distribution[range_name] >= 0


def test_statistics_distribution_sum(test_client):
    """Test that distribution counts sum to total applications."""
    response = test_client.get("/statistics")
    
    assert response.status_code == 200
    data = response.json()
    
    distribution = data["score_distribution"]
    total_in_distribution = sum(distribution.values())
    
    # Sum of distribution should equal total applications
    assert total_in_distribution == data["total_applications"]


def test_statistics_consistency(test_client):
    """Test that statistics are internally consistent."""
    response = test_client.get("/statistics")
    
    assert response.status_code == 200
    data = response.json()
    
    # If there are applications, average should be between min and max
    if data["total_applications"] > 0:
        assert data["min_score"] <= data["average_score"] <= data["max_score"]
        
        # Median should also be between min and max
        assert data["min_score"] <= data["median_score"] <= data["max_score"]

# Made with Bob
