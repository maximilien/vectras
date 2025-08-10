# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for Vectras supervisor agent."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.supervisor import SupervisorAgent, create_app


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
def supervisor_agent(monkeypatch, temp_project):
    """Create a supervisor agent with fake OpenAI."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    # Mock the project root to use our temp directory
    with patch("vectras.agents.supervisor.get_project_root", return_value=temp_project):
        agent = SupervisorAgent()
        yield agent


def test_supervisor_agent_initialization(supervisor_agent):
    """Test supervisor agent initializes correctly."""
    assert supervisor_agent.agent_id == "supervisor"
    assert supervisor_agent.config is not None
    assert supervisor_agent.project_root is not None


@pytest.mark.asyncio
async def test_get_project_files(supervisor_agent):
    """Test getting project files."""
    files = await supervisor_agent.get_project_files()
    assert isinstance(files, list)
    assert any("test.py" in f for f in files)


@pytest.mark.asyncio
async def test_read_file(supervisor_agent):
    """Test reading project files."""
    content = await supervisor_agent.read_file("test.py")
    assert content == "print('hello world')"

    # Test non-existent file
    content = await supervisor_agent.read_file("nonexistent.py")
    assert content is None


@pytest.mark.asyncio
async def test_user_settings(supervisor_agent):
    """Test user settings management."""
    # Get initial settings
    settings = await supervisor_agent.get_user_settings()
    assert isinstance(settings, dict)
    assert "project_name" in settings

    # Update settings
    updates = {"test_key": "test_value"}
    success = await supervisor_agent.update_user_settings(updates)
    assert success

    # Verify update
    updated_settings = await supervisor_agent.get_user_settings()
    assert updated_settings["test_key"] == "test_value"


@pytest.mark.asyncio
async def test_check_services_health(supervisor_agent):
    """Test service health checking."""
    # Mock httpx client responses
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        health = await supervisor_agent.check_services_health()
        assert isinstance(health, dict)
        assert "api" in health
        assert "mcp" in health


@pytest.mark.asyncio
async def test_query_processing(supervisor_agent):
    """Test query processing."""
    # Test status query
    response = await supervisor_agent.process_query("tell me the status on the backend")
    assert isinstance(response, dict)

    # Test file listing
    response = await supervisor_agent.process_query("list files")
    assert isinstance(response, list)

    # Test general query (should use LLM)
    response = await supervisor_agent.process_query("hello world")
    assert isinstance(response, str)
    assert "FAKE_OPENAI_RESPONSE" in response


def test_supervisor_fastapi_app(monkeypatch):
    """Test the FastAPI app endpoints."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    app = create_app()
    client = TestClient(app)

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Test status endpoint
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "agent_id" in data
    assert data["agent_id"] == "supervisor"

    # Test query endpoint
    response = client.post("/query", json={"query": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "FAKE_OPENAI_RESPONSE" in data["response"]


@pytest.mark.asyncio
async def test_handoff_functionality(supervisor_agent):
    """Test agent handoff functionality."""
    # Mock the handoff to another agent
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "response": "mock response",
            "agent_id": "log-monitor",
            "timestamp": "2024-01-01T00:00:00",
        }

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # Test handoff
        response = await supervisor_agent.handoff_to_agent("log-monitor", "check logs")
        assert response.status == "success"
        assert response.agent_id == "log-monitor"


def test_agent_status(supervisor_agent):
    """Test agent status tracking."""
    status = supervisor_agent.get_status()
    assert status.agent_id == "supervisor"
    assert status.status in ["idle", "active"]
    assert isinstance(status.uptime_seconds, float)
    assert status.uptime_seconds >= 0


def test_activity_logging(supervisor_agent):
    """Test activity logging."""
    initial_count = len(supervisor_agent.recent_activities)

    supervisor_agent.log_activity("test_activity", {"key": "value"})

    assert len(supervisor_agent.recent_activities) == initial_count + 1
    latest_activity = supervisor_agent.recent_activities[-1]
    assert latest_activity["activity"] == "test_activity"
    assert latest_activity["details"]["key"] == "value"
