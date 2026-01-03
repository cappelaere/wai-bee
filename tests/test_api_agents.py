"""Tests for API agent configuration endpoints.

This module tests the agent configuration retrieval endpoints of the API.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-10
Version: 1.0.0
License: MIT
"""

import pytest


def test_get_agents_config(test_client, scholarship_name):
    """Test getting complete agent configuration."""
    response = test_client.get(f"/agents?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "scholarship_name" in data
    assert "description" in data
    assert "version" in data
    assert "agents" in data
    assert "scoring_agents" in data
    assert "total_weight" in data
    
    assert data["scholarship_name"] == scholarship_name
    assert isinstance(data["agents"], list)
    assert len(data["agents"]) > 0


def test_agents_config_structure(test_client, scholarship_name):
    """Test that agent configuration has expected structure."""
    response = test_client.get(f"/agents?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check each agent has required fields
    for agent in data["agents"]:
        assert "name" in agent
        assert "display_name" in agent
        assert "description" in agent
        assert "enabled" in agent
        assert "required" in agent
        
        # Scoring agents should have weight
        if agent["name"] in data["scoring_agents"]:
            assert "weight" in agent
            assert isinstance(agent["weight"], (int, float))


def test_get_application_agent(test_client, scholarship_name):
    """Test getting application agent configuration."""
    response = test_client.get(f"/agents/application?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "scholarship" in data
    assert "agent" in data
    
    agent = data["agent"]
    assert agent["name"] == "application"
    assert agent["display_name"] == "Application Agent"
    assert "weight" in agent
    assert agent["weight"] == 0.20


def test_get_resume_agent(test_client, scholarship_name):
    """Test getting resume agent configuration."""
    response = test_client.get(f"/agents/resume?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    agent = data["agent"]
    assert agent["name"] == "resume"
    assert agent["weight"] == 0.25


def test_get_essay_agent(test_client, scholarship_name):
    """Test getting essay agent configuration."""
    response = test_client.get(f"/agents/essay?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    agent = data["agent"]
    assert agent["name"] == "essay"
    assert agent["weight"] == 0.30


def test_get_recommendation_agent(test_client, scholarship_name):
    """Test getting recommendation agent configuration."""
    response = test_client.get(f"/agents/recommendation?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    agent = data["agent"]
    assert agent["name"] == "recommendation"
    assert agent["weight"] == 0.25


def test_get_attachment_agent(test_client, scholarship_name):
    """Test getting attachment agent configuration."""
    response = test_client.get(f"/agents/attachment?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    agent = data["agent"]
    assert agent["name"] == "attachment"
    # Attachment agent doesn't have weight (not a scoring agent)
    assert agent["weight"] is None


def test_get_invalid_agent(test_client, scholarship_name):
    """Test getting configuration for non-existent agent."""
    response = test_client.get(f"/agents/invalid_agent?scholarship={scholarship_name}")
    
    assert response.status_code == 404
    data = response.json()
    
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_scoring_agents_weights_sum_to_one(test_client, scholarship_name):
    """Test that scoring agent weights sum to 1.0."""
    response = test_client.get(f"/agents?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Calculate total weight from scoring agents
    total_weight = 0.0
    for agent in data["agents"]:
        if agent["name"] in data["scoring_agents"] and agent["weight"] is not None:
            total_weight += agent["weight"]
    
    # Should sum to 1.0 (with small tolerance for floating point)
    assert abs(total_weight - 1.0) < 0.01


def test_all_scoring_agents_have_weights(test_client, scholarship_name):
    """Test that all scoring agents have defined weights."""
    response = test_client.get(f"/agents?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    scoring_agents = data["scoring_agents"]
    
    for agent in data["agents"]:
        if agent["name"] in scoring_agents:
            assert agent["weight"] is not None
            assert agent["weight"] > 0


def test_agent_evaluates_field(test_client, scholarship_name):
    """Test that agents have evaluates field with content."""
    response = test_client.get(f"/agents/application?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    agent = data["agent"]
    assert "evaluates" in agent
    assert isinstance(agent["evaluates"], list)
    assert len(agent["evaluates"]) > 0


def test_agent_criteria_field(test_client, scholarship_name):
    """Test that scoring agents have criteria field."""
    response = test_client.get(f"/agents/resume?scholarship={scholarship_name}")
    
    assert response.status_code == 200
    data = response.json()
    
    agent = data["agent"]
    assert "criteria" in agent
    # Scoring agents should have criteria file path
    if agent["name"] in ["application", "resume", "essay", "recommendation"]:
        assert agent["criteria"] is not None
        assert "criteria" in agent["criteria"]


# Made with Bob