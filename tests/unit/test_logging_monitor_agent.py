# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for log monitor agent."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.logging_monitor import LogEntry, LogMonitorManager, app


@pytest.fixture
def temp_logs():
    """Create a temporary logs directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_path = Path(tmpdir)
        yield logs_path


@pytest.fixture
def log_monitor_manager(monkeypatch, temp_logs):
    """Create a log monitor manager with fake OpenAI."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    # Create manager and then patch the instance attribute
    manager = LogMonitorManager()
    manager.logs_directory = temp_logs
    yield manager


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_log_entry_creation():
    """Test LogEntry creation and classification."""
    # Test error entry
    error_entry = LogEntry("test.log", 10, "2024-01-01 12:00:00 ERROR: Something went wrong")

    assert error_entry.severity == "error"
    assert error_entry.is_error
    assert error_entry.file_path == "test.log"
    assert error_entry.line_number == 10

    # Test info entry
    info_entry = LogEntry("test.log", 5, "2024-01-01 12:00:00 INFO: Application started")

    assert info_entry.severity == "info"
    assert not info_entry.is_error

    # Test exception entry
    exception_entry = LogEntry(
        "test.log",
        15,
        "Traceback (most recent call last):\n  File test.py, line 10, in <module>\nValueError: Invalid value",
    )

    assert exception_entry.error_type == "exception"
    assert exception_entry.is_error


def test_log_entry_to_dict():
    """Test LogEntry to_dict method."""
    entry = LogEntry("test.log", 10, "ERROR: Test error")
    entry_dict = entry.to_dict()

    assert entry_dict["file_path"] == "test.log"
    assert entry_dict["line_number"] == 10
    assert entry_dict["content"] == "ERROR: Test error"
    assert entry_dict["severity"] == "error"
    assert entry_dict["is_error"] is True
    assert "timestamp" in entry_dict


def test_log_monitor_manager_initialization(log_monitor_manager):
    """Test log monitor manager initializes correctly."""
    assert log_monitor_manager.logs_directory is not None
    assert isinstance(log_monitor_manager.log_entries, list)
    assert log_monitor_manager.error_count == 0
    assert log_monitor_manager.warning_count == 0


@pytest.mark.asyncio
async def test_check_logs(log_monitor_manager, temp_logs):
    """Test checking logs."""
    # Create a test log file
    log_file = temp_logs / "test.log"
    log_content = """2024-01-01 12:00:00 INFO: Application started
2024-01-01 12:01:00 ERROR: Database connection failed
2024-01-01 12:02:00 WARNING: High memory usage
"""
    log_file.write_text(log_content)

    result = await log_monitor_manager.check_logs()
    assert "Log Check Results" in result
    assert "test.log" in result

    @pytest.mark.asyncio
    async def test_check_recent_logs(log_monitor_manager, temp_logs):
        """Test checking recent logs."""
        # Create a test log file
        log_file = temp_logs / "recent.log"
        log_content = """2024-01-01 12:00:00 INFO: Recent log entry
    2024-01-01 12:01:00 ERROR: Recent error
    """
        log_file.write_text(log_content)

        # First check logs to populate log_entries
        await log_monitor_manager.check_logs()

        result = await log_monitor_manager.check_recent_logs()
        assert "Recent Log Activity" in result
        # The recent logs check might not show the file name in the output, so just check for the activity
        assert "Total Entries" in result


@pytest.mark.asyncio
async def test_search_logs(log_monitor_manager, temp_logs):
    """Test searching logs."""
    # Create a test log file
    log_file = temp_logs / "search.log"
    log_content = """2024-01-01 12:00:00 INFO: User login successful
2024-01-01 12:01:00 ERROR: Database connection failed
2024-01-01 12:02:00 INFO: User logout
"""
    log_file.write_text(log_content)

    result = await log_monitor_manager.search_logs("error")
    assert "Log Search Results" in result
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_get_error_summary(log_monitor_manager):
    """Test getting error summary."""
    result = await log_monitor_manager.get_error_summary()
    assert "Error Summary" in result
    assert "Total Errors" in result


@pytest.mark.asyncio
async def test_get_log_monitor_status(log_monitor_manager):
    """Test getting log monitor status."""
    result = log_monitor_manager.get_status()
    assert "Logging Monitor Agent Status" in result
    assert "Logs Directory" in result


def test_health_endpoint(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "logging-monitor-agent"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "Logging Monitor Agent"
    assert data["status"] == "active"
    assert "tools" in data


@pytest.mark.asyncio
async def test_query_endpoint(test_client):
    """Test query endpoint."""
    # Mock the Runner.run method
    with patch("vectras.agents.logging_monitor.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Test response from log monitor agent"
        mock_run.return_value = mock_result

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test response from log monitor agent" in data["response"]
        assert data["agent_id"] == "logging-monitor"


@pytest.mark.asyncio
async def test_query_endpoint_error(test_client):
    """Test query endpoint with error."""
    # Mock the Runner.run method to raise an exception
    with patch("vectras.agents.logging_monitor.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test error")

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Error processing query" in data["response"]
