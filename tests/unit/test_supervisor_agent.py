# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for Vectras supervisor agent."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.supervisor import SupervisorManager, app


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create some test files
        (project_path / "test.py").write_text("print('hello world')")
        (project_path / "config").mkdir()
        (project_path / "config" / "test.yaml").write_text("test: value")

        yield project_path


@pytest.fixture
def supervisor_manager(monkeypatch, temp_project):
    """Create a supervisor manager with fake OpenAI."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    # Create manager and then patch the instance attribute
    manager = SupervisorManager()
    manager.project_root = temp_project
    yield manager


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_supervisor_manager_initialization(supervisor_manager):
    """Test supervisor manager initializes correctly."""
    assert supervisor_manager.project_root is not None
    assert supervisor_manager.user_settings_path is not None
    assert "github" in supervisor_manager.agent_endpoints
    assert "testing" in supervisor_manager.agent_endpoints


@pytest.mark.asyncio
async def test_get_project_files(supervisor_manager):
    """Test getting project files."""
    result = await supervisor_manager.get_project_files()
    assert isinstance(result, str)
    assert "Project Files" in result
    assert "test.py" in result


@pytest.mark.asyncio
async def test_read_file(supervisor_manager):
    """Test reading project files."""
    content = await supervisor_manager.read_file("test.py")
    assert isinstance(content, str)
    assert "print('hello world')" in content

    # Test non-existent file
    content = await supervisor_manager.read_file("nonexistent.py")
    assert "not found" in content


@pytest.mark.asyncio
async def test_user_settings(supervisor_manager):
    """Test user settings management."""
    # Get initial settings
    settings = await supervisor_manager.get_user_settings()
    assert isinstance(settings, str)
    assert "User Settings" in settings

    # Update settings
    updates = {"test_key": "test_value"}
    result = await supervisor_manager.update_user_settings(updates)
    assert isinstance(result, str)
    assert "Settings Updated" in result


@pytest.mark.asyncio
async def test_check_agent_health(supervisor_manager):
    """Test agent health checking."""
    # Mock httpx client responses
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

    result = await supervisor_manager.check_agent_health()
    assert isinstance(result, str)
    assert "Health Check" in result


@pytest.mark.asyncio
async def test_get_agent_status(supervisor_manager):
    """Test getting agent status."""
    # Mock httpx client responses
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "agent": "Testing Agent",
            "status": "active",
            "tools": ["test_tool"],
        }

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

    result = await supervisor_manager.get_agent_status()
    assert isinstance(result, str)
    assert "Agent Status" in result


@pytest.mark.asyncio
async def test_get_project_summary(supervisor_manager):
    """Test getting project summary."""
    result = await supervisor_manager.get_project_summary()
    assert isinstance(result, str)
    assert "Project Summary" in result


@pytest.mark.asyncio
async def test_get_supervisor_status(supervisor_manager):
    """Test getting supervisor status."""
    result = supervisor_manager.get_status()
    assert isinstance(result, str)
    assert "Supervisor Agent Status" in result


def test_health_endpoint(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "supervisor-agent"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "Supervisor Agent"
    assert data["status"] == "active"
    assert "tools" in data


@pytest.mark.asyncio
async def test_query_endpoint(test_client):
    """Test query endpoint."""
    # Mock the Runner.run method
    with patch("vectras.agents.supervisor.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Test response from supervisor"
        mock_run.return_value = mock_result

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test response from supervisor" in data["response"]
        assert data["agent_id"] == "supervisor"


@pytest.mark.asyncio
async def test_query_endpoint_error(test_client):
    """Test query endpoint with error."""
    # Mock the Runner.run method to raise an exception
    with patch("vectras.agents.supervisor.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test error")

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Error processing query" in data["response"]
