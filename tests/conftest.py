"""Pytest configuration and fixtures for API tests.

This module provides shared fixtures for testing the Bee Agents API.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import pytest
from fastapi.testclient import TestClient
from bee_agents.api import app, initialize_service


# Test scholarship name
TEST_SCHOLARSHIP = "Delaney_Wings"


@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the API.
    
    This fixture initializes the API with test data and provides
    a TestClient for making requests.
    
    Yields:
        TestClient: FastAPI test client
    """
    # Initialize the service with Delaney_Wings scholarship
    initialize_service(TEST_SCHOLARSHIP, "outputs")
    
    # Create test client
    client = TestClient(app)
    
    yield client
    
    # Cleanup if needed
    pass


@pytest.fixture(scope="module")
def scholarship_name():
    """Provide the test scholarship name.
    
    Returns:
        str: The scholarship name used for testing
    """
    return TEST_SCHOLARSHIP


@pytest.fixture(scope="module")
def sample_wai_number(test_client, scholarship_name):
    """Get a sample WAI number for testing.
    
    Args:
        test_client: FastAPI test client
        scholarship_name: Name of the test scholarship
        
    Returns:
        str: A valid WAI number from the test data
    """
    # Get top scores to find a valid WAI number
    response = test_client.get(f"/top_scores?scholarship={scholarship_name}&limit=1")
    if response.status_code == 200:
        data = response.json()
        if data.get("top_scores"):
            return data["top_scores"][0]["wai_number"]
    
    # Fallback to a known WAI number
    return "75179"


@pytest.fixture
def invalid_wai_number():
    """Provide an invalid WAI number for testing error cases.
    
    Returns:
        str: An invalid WAI number
    """
    return "99999999"

# Made with Bob
