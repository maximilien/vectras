# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for testing agent."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.testing import TestingAgentManager, TestingTool, app


@pytest.fixture
def testing_manager():
    """Create a testing manager for tests."""
    return TestingAgentManager()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_testing_tool_creation():
    """Test TestingTool creation."""
    tool = TestingTool(
        name="test_tool", language="python", code="print('hello')", description="A test tool"
    )

    assert tool.name == "test_tool"
    assert tool.language == "python"
    assert tool.code == "print('hello')"
    assert tool.description == "A test tool"
    assert tool.has_bugs is False
    assert tool.severity == "low"
    assert tool.id is not None


def test_testing_tool_to_dict():
    """Test TestingTool to_dict method."""
    tool = TestingTool(
        name="test_tool", language="python", code="print('hello')", description="A test tool"
    )

    tool_dict = tool.to_dict()
    assert tool_dict["name"] == "test_tool"
    assert tool_dict["language"] == "python"
    assert tool_dict["code"] == "print('hello')"
    assert tool_dict["description"] == "A test tool"
    assert "id" in tool_dict
    assert "created_at" in tool_dict


def test_testing_manager_initialization(testing_manager):
    """Test testing manager initializes correctly."""
    assert testing_manager.test_tools_directory == Path("./test_tools")
    assert isinstance(testing_manager.test_tools, dict)
    assert len(testing_manager.test_tools) > 0  # Should have sample tools


@pytest.mark.asyncio
async def test_create_testing_tool(testing_manager):
    """Test creating a testing tool."""
    result = testing_manager.create_tool(
        name="calculator",
        language="python",
        description="A simple calculator",
        code="def add(a, b): return a + b",
    )

    assert "Successfully created tool" in result
    assert any(tool.name == "calculator" for tool in testing_manager.test_tools.values())


@pytest.mark.asyncio
async def test_list_testing_tools(testing_manager):
    """Test listing testing tools."""
    result = testing_manager.list_tools()

    assert "Available testing tools" in result
    assert "calculator" in result
    # Should include sample tools
    assert any(tool.name == "calculator" for tool in testing_manager.test_tools.values())


@pytest.mark.asyncio
async def test_execute_testing_tool_success(testing_manager):
    """Test successful tool execution."""
    # Create a simple tool first
    testing_manager.create_tool(
        name="simple_print",
        language="python",
        description="Simple print tool",
        code="print('Hello, World!')",
    )

    # Find the tool
    tool = None
    for t in testing_manager.test_tools.values():
        if t.name == "simple_print":
            tool = t
            break

    assert tool is not None

    result = testing_manager.execute_tool("simple_print", "Hello, World!")
    assert "executed successfully" in result
    assert "simple_print" in result


@pytest.mark.asyncio
async def test_execute_testing_tool_not_found(testing_manager):
    """Test executing non-existent tool."""
    result = testing_manager.execute_tool("nonexistent-id", "test")
    assert "not found" in result


@pytest.mark.asyncio
async def test_run_tool_tests(testing_manager):
    """Test running tool tests."""
    result = testing_manager.run_tests("calculator")
    assert "Tests for" in result


@pytest.mark.asyncio
async def test_get_testing_status(testing_manager):
    """Test getting testing status."""
    result = testing_manager.get_status()
    assert "Testing Agent Status" in result
    assert "Total Tools" in result


@pytest.mark.asyncio
async def test_reload_testing_tools(testing_manager):
    """Test reloading testing tools."""
    initial_count = len(testing_manager.test_tools)
    result = testing_manager.reload_tools()

    assert "Reloaded tools" in result
    assert len(testing_manager.test_tools) >= initial_count


def test_health_endpoint(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "testing-agent"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "Testing Agent"
    assert data["status"] == "active"
    assert "tools" in data


@pytest.mark.asyncio
async def test_query_endpoint(test_client):
    """Test query endpoint."""
    # Mock the Runner.run method
    with patch("vectras.agents.testing.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Test response from testing agent"
        mock_run.return_value = mock_result

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test response from testing agent" in data["response"]
        assert data["agent_id"] == "testing"


@pytest.mark.asyncio
async def test_query_endpoint_error(test_client):
    """Test query endpoint with error."""
    # Mock the Runner.run method to raise an exception
    with patch("vectras.agents.testing.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test error")

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Error processing query" in data["response"]
