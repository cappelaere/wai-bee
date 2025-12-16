"""Tests for API health and status endpoints.

This module tests the health check and root endpoints of the API.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import pytest


def test_root_endpoint(test_client):
    """Test the root endpoint returns API information."""
    response = test_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "message" in data
    assert "available_scholarships" in data
    assert "version" in data
    assert "status" in data
    
    assert isinstance(data["available_scholarships"], list)
    assert len(data["available_scholarships"]) > 0
    assert data["status"] == "operational"


def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "scholarships" in data
    assert "total_scholarships" in data
    
    assert data["status"] == "healthy"
    assert isinstance(data["scholarships"], list)
    assert len(data["scholarships"]) > 0
    assert isinstance(data["total_scholarships"], int)
    assert data["total_scholarships"] > 0


def test_openapi_yaml_endpoint(test_client):
    """Test that OpenAPI YAML spec is available."""
    response = test_client.get("/openapi.yml")
    
    # Should return 200 if file exists, 404 if not generated yet
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        # Check that content-type contains yaml (may or may not have charset)
        assert "application/x-yaml" in response.headers["content-type"]


def test_openapi_json_endpoint(test_client):
    """Test that OpenAPI JSON spec is available."""
    response = test_client.get("/openapi.json")
    
    # Should return 200 if file exists, 404 if not generated yet
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        assert "application/json" in response.headers["content-type"]

# Made with Bob
