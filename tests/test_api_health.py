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
    """Test the enhanced health check endpoint."""
    response = test_client.get("/health")
    
    # Should return 200 for healthy or 503 for degraded
    assert response.status_code in [200, 503]
    data = response.json()
    
    # Check top-level fields
    assert "status" in data
    assert "timestamp" in data
    assert "checks" in data
    
    # Check status is either healthy or degraded
    assert data["status"] in ["healthy", "degraded"]
    
    # Check that all required checks are present
    checks = data["checks"]
    assert "data_services" in checks
    assert "disk_space" in checks
    assert "directories" in checks
    assert "configuration" in checks
    
    # Verify data_services check structure
    data_services = checks["data_services"]
    assert "status" in data_services
    assert "scholarships" in data_services
    assert "total_scholarships" in data_services
    assert isinstance(data_services["scholarships"], list)
    assert isinstance(data_services["total_scholarships"], int)
    
    # Verify disk_space check structure
    disk_space = checks["disk_space"]
    assert "status" in disk_space
    
    # Verify directories check structure
    directories = checks["directories"]
    assert "status" in directories
    assert "data_dir_exists" in directories
    assert "outputs_dir_exists" in directories
    
    # Verify configuration check structure
    configuration = checks["configuration"]
    assert "status" in configuration
    assert "user_config_exists" in configuration


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
