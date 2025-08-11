# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for log monitor agent."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.log_monitor import LogEntry, LogMonitorAgent, create_app


@pytest.fixture
def temp_logs():
    """Create a temporary logs directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_path = Path(tmpdir)
        yield logs_path


@pytest.fixture
def log_monitor_agent(monkeypatch, temp_logs):
    """Create a log monitor agent with fake OpenAI."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    # Mock the logs directory to use our temp directory
    with patch("vectras.agents.log_monitor.get_logs_directory", return_value=temp_logs):
        agent = LogMonitorAgent()
        yield agent


def test_log_entry_creation():
    """Test LogEntry creation and classification."""
    # Test error entry
    error_entry = LogEntry("test.log", 10, "2024-01-01 12:00:00 ERROR: Something went wrong")

    assert error_entry["severity"] == "error"
    assert error_entry.is_error
    assert error_entry["file_path"] == "test.log"
    assert error_entry["line_number"] == 10

    # Test info entry
    info_entry = LogEntry("test.log", 5, "2024-01-01 12:00:00 INFO: Application started")

    assert info_entry["severity"] == "info"
    assert not info_entry.is_error

    # Test exception entry
    exception_entry = LogEntry(
        "test.log",
        15,
        "Traceback (most recent call last):\n  File test.py, line 10, in <module>\nValueError: Invalid value",
    )

    assert exception_entry["error_type"] == "exception"
    assert exception_entry.is_error


def test_log_monitor_initialization(log_monitor_agent):
    """Test log monitor agent initializes correctly."""
    assert log_monitor_agent.agent_id == "log-monitor"
    assert log_monitor_agent.config is not None
    assert log_monitor_agent.logs_directory is not None
    assert isinstance(log_monitor_agent.error_patterns, list)


@pytest.mark.asyncio
async def test_process_log_line(log_monitor_agent):
    """Test processing individual log lines."""
    initial_errors = len(log_monitor_agent.recent_errors)

    # Process an error line
    await log_monitor_agent.process_log_line("test.log", 1, "ERROR: Test error message")

    # Should have added an error
    assert len(log_monitor_agent.recent_errors) == initial_errors + 1

    # Process a normal line
    await log_monitor_agent.process_log_line("test.log", 2, "INFO: Normal log message")

    # Should not have added an error
    assert len(log_monitor_agent.recent_errors) == initial_errors + 1


@pytest.mark.asyncio
async def test_process_log_file(log_monitor_agent, temp_logs):
    """Test processing log files."""
    # Create a test log file
    log_file = temp_logs / "test.log"
    log_content = """2024-01-01 12:00:00 INFO: Application started
2024-01-01 12:01:00 ERROR: Database connection failed
2024-01-01 12:02:00 WARNING: Retrying connection
2024-01-01 12:03:00 CRITICAL: System failure
"""
    log_file.write_text(log_content)

    # Process the file
    await log_monitor_agent.process_log_file(str(log_file))

    # Should have detected errors
    assert len(log_monitor_agent.recent_errors) >= 2  # ERROR and CRITICAL lines


@pytest.mark.asyncio
async def test_get_recent_errors(log_monitor_agent):
    """Test getting recent errors."""
    # Add some test errors
    error1 = LogEntry("test1.log", 1, "ERROR: First error")
    error2 = LogEntry("test2.log", 2, "CRITICAL: Second error")

    log_monitor_agent.recent_errors.extend([error1, error2])

    # Get recent errors
    recent = await log_monitor_agent.get_recent_errors(limit=10)
    assert len(recent) >= 2

    # Test severity filtering
    critical_errors = await log_monitor_agent.get_recent_errors(severity="critical")
    assert len(critical_errors) >= 1


@pytest.mark.asyncio
async def test_get_error_summary(log_monitor_agent):
    """Test getting error summary."""
    # Add some test errors with recent timestamps
    error1 = LogEntry("test1.log", 1, "ERROR: Database error")
    error2 = LogEntry("test2.log", 2, "Exception in thread")
    error3 = LogEntry("test3.log", 3, "CRITICAL: System failure")

    log_monitor_agent.recent_errors.extend([error1, error2, error3])

    # Get summary
    summary = await log_monitor_agent.get_error_summary(hours=24)

    assert "total_errors" in summary
    assert "error_types" in summary
    assert "severity_counts" in summary
    assert "files_with_errors" in summary
    assert summary["total_errors"] >= 3


@pytest.mark.asyncio
async def test_notify_code_fixer(log_monitor_agent):
    """Test notifying code fixer agent."""
    critical_error = LogEntry("test.py", 10, "CRITICAL: SyntaxError at line 10")

    # Mock the handoff
    with patch.object(
        log_monitor_agent, "handoff_to_agent", new_callable=AsyncMock
    ) as mock_handoff:
        await log_monitor_agent.notify_code_fixer(critical_error)

        # Should have called handoff
        mock_handoff.assert_called_once()
        args, kwargs = mock_handoff.call_args
        assert args[0] == "coding"  # target agent
        assert "SyntaxError" in args[1]  # query contains error


@pytest.mark.asyncio
async def test_query_processing(log_monitor_agent):
    """Test query processing."""
    # Test status query
    response = await log_monitor_agent.process_query("status")
    assert isinstance(response, dict)
    assert "monitoring" in response

    # Test recent errors query
    response = await log_monitor_agent.process_query("show recent errors")
    assert isinstance(response, str)
    assert "recent errors" in response.lower() or "no recent errors" in response.lower()

    # Test error summary query
    response = await log_monitor_agent.process_query("error summary")
    assert isinstance(response, dict)
    assert "total_errors" in response

    # Test general query (should use LLM)
    response = await log_monitor_agent.process_query("hello world")
    assert isinstance(response, str)
    assert "Monitoring logs for errors and issues" in response


def test_log_monitor_fastapi_app(monkeypatch):
    """Test the FastAPI app endpoints."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vectras.agents.log_monitor.get_logs_directory", return_value=Path(tmpdir)):
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
            assert data["agent_id"] == "log-monitor"

            # Test query endpoint
            response = client.post("/query", json={"query": "status"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


@pytest.mark.asyncio
async def test_monitoring_control(log_monitor_agent):
    """Test starting and stopping monitoring."""
    # Test start monitoring
    response = await log_monitor_agent.process_query("start monitoring")
    assert isinstance(response, dict)
    assert "status" in response

    # Test stop monitoring
    response = await log_monitor_agent.process_query("stop monitoring")
    assert isinstance(response, dict)
    assert "status" in response


def test_error_detection_patterns():
    """Test error detection with various patterns."""
    patterns = [
        ("ERROR: Database failed", True),
        ("Exception in thread main", True),
        ("Traceback (most recent call last)", True),
        ("FATAL: System crash", True),
        ("CRITICAL: Memory exhausted", True),
        ("INFO: Application started", False),
        ("DEBUG: Processing request", False),
        ("WARNING: Deprecated method", False),
    ]

    for content, should_be_error in patterns:
        entry = LogEntry("test.log", 1, content)
        assert entry.is_error == should_be_error, f"Failed for: {content}"


@pytest.mark.asyncio
async def test_file_monitoring_setup(log_monitor_agent):
    """Test file monitoring setup."""
    # Monitoring should start automatically
    await log_monitor_agent.start_monitoring()
    assert log_monitor_agent.monitoring

    # Stop monitoring
    await log_monitor_agent.stop_monitoring()
    assert not log_monitor_agent.monitoring
